import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(page_title="Strict Deal Assistant", layout="wide", page_icon="✈️")

# --- 2. DATA LOAD ---
# Using the export link for your specific sheet
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

# --- 3. THE "STRICT" DATE CONVERTER ---
def get_date_score(text):
    """Converts 'Dec 2026' or '31 Mar 26' into a comparable integer (YYYYMM)."""
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # 1. Extract Month
    found_m = 0
    for m_name, m_val in months.items():
        if m_name in text:
            found_m = m_val
            break
            
    # 2. Extract Year (Handles 2026 or 26)
    year_match = re.search(r'(20\d{2})|(\d{2})$|(\d{2})\s', text)
    found_y = 0
    if year_match:
        y_str = year_match.group().strip().replace("'", "")
        found_y = int(y_str) if len(y_str) == 4 else int("20" + y_str)

    if found_m > 0 and found_y > 0:
        # Returns a number like 202612
        return (found_y * 100) + found_m
    return None

# --- 4. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_airline" not in st.session_state:
    st.session_state.current_airline = None

# --- 5. UI ---
st.title("✈️ Airline Deal Assistant")
st.write("Strict Date Validation: Active")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(pd.DataFrame([msg["data"]]), use_container_width=True)

# --- 6. LOGIC ---
if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    # Identify Airline
    found_row = None
    for _, row in df.iterrows():
        name, iata = str(row.get('airlines name', '')).lower(), str(row.get('airlines', '')).lower()
        if iata in query or (len(name) > 3 and name in query):
            st.session_state.current_airline = row
            found_row = row
            break
    
    # Identify Cabin
    cabin = next((c for c in ["bus", "eco", "first", "prem. eco"] if c in query or ("business" in query and c=="bus") or ("economy" in query and c=="eco")), None)

    # Date Check
    req_score = get_date_score(query)

    with st.chat_message("assistant"):
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            airline_name = str(active_row.get('airlines name', 'UNKNOWN')).upper()
            val_str = str(active_row.get('validity', ''))
            val_score = get_date_score(val_str)

            # --- THE LOCKDOWN CHECK ---
            if req_score and val_score and req_score > val_score:
                response = f"❌ **No Available Deal for these dates.**\n\nThe current deals for **{airline_name}** are only valid until **{val_str}**. Your requested travel date is past this period."
                display_data = None 
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
            resp = "I couldn't find that airline. Please try searching by name or IATA code (e.g., EY)."
            st.write(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp, "data": None})
