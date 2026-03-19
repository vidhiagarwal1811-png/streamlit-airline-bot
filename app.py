import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Airline Deal Assistant", layout="wide", page_icon="✈️")

# --- 2. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. THE "STRICT" DATE PARSER ---
def get_comparable_date(text):
    """Converts text like '31 MAR 26' or 'dec 2026' into a datetime object."""
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    
    # Month Map
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    found_month = None
    for m_name, m_val in months.items():
        if m_name in text:
            found_month = m_val
            break
            
    # Find Year (looks for 2026 or just 26)
    year_match = re.search(r'(20\d{2})|(\d{2})$|(\d{2})\s', text)
    found_year = None
    if year_match:
        year_str = year_match.group().strip().replace("'", "")
        found_year = int(year_str) if len(year_str) == 4 else int("20" + year_str)

    if found_month and found_year:
        return datetime(found_year, found_month, 1)
    return None

# --- 4. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_airline" not in st.session_state:
    st.session_state.current_airline = None

# --- 5. UI ---
st.title("✈️ Airline Deal Assistant")
st.write("Current Rules: If travel date > validity, **No Deal** will be shown.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(pd.DataFrame([msg["data"]]), use_container_width=True)

# --- 6. LOGIC ---
if user_input := st.chat_input("Ex: 'EY dec 2026'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    # A. Search for Airline (EY, AI, name)
    found_row = None
    for _, row in df.iterrows():
        name = str(row.get('airlines name', '')).lower()
        iata = str(row.get('airlines', '')).lower()
        if iata in query or (len(name) > 3 and name in query):
            st.session_state.current_airline = row
            found_row = row
            break
    
    # B. Identify Cabin
    cabin = None
    if any(x in query for x in ["bus", "business"]): cabin = "bus"
    elif any(x in query for x in ["eco", "economy"]): cabin = "eco"
    elif any(x in query for x in ["prem", "premium"]): cabin = "prem. eco"
    elif "first" in query: cabin = "first"

    # C. Date Validation
    req_date = get_comparable_date(query)

    with st.chat_message("assistant"):
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            airline_name = str(active_row.get('airlines name', 'UNKNOWN')).upper()
            val_str = str(active_row.get('validity', ''))
            val_date = get_comparable_date(val_str)

            # --- THE LOCKDOWN CHECK ---
            if req_date and val_date and req_date > val_date:
                response = f"❌ **No Available Deal for these dates.**\n\nExisting deals for **{airline_name}** expired on **{val_str}**. Please try a date before April 2026."
                display_data = None # Hide the row
            else:
                if cabin:
                    price = active_row.get(cabin, "N/A")
                    response = f"✅ Deal Found! **{airline_name}** {cabin.upper()} is **{price}** (Valid: {val_str})."
                else:
                    response = f"I found the deals for **{airline_name}** (Valid: {val_str}). Which cabin (Eco/Bus) do you need?"
                display_data = active_row
            
            st.write(response)
            if display_data is not None:
                st.dataframe(pd.DataFrame([display_data]), use_container_width=True)
            
            st.session_state.messages.append({"role": "assistant", "content": response, "data": display_data})
        else:
            resp = "Airline not found. Try 'EY' or 'Air India'."
            st.write(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp, "data": None})
