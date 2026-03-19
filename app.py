import streamlit as st
import pandas as pd
import re

# --- 1. SETUP ---
st.set_page_config(page_title="Strict Deal Bot", layout="wide")

# --- 2. DATA LOAD ---
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

# --- 3. THE NUMERIC DATE SCORER ---
def get_date_score(text):
    """Converts 'Dec 2026' or '31 Mar 26' into a comparable number like 202612."""
    if not text or pd.isna(text): return None
    text = str(text).lower()
    
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    
    # Extract Month
    m_val = next((v for k, v in months.items() if k in text), 0)
    
    # Extract Year (Handles 2026 or 26)
    y_match = re.search(r'(20\d{2})|(?<=\s)(\d{2})$|(?<=-)(\d{2})$|(\d{2})\s|(\d{2})$', text)
    
    if m_val > 0 and y_match:
        y_str = "".join(filter(str.isdigit, y_match.group()))
        y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
        return (y_val * 100) + m_val
    return None

# --- 4. SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []

# --- 5. UI ---
st.title("✈️ Airline Deal Assistant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "table" in msg and msg["table"] is not None:
            st.dataframe(pd.DataFrame([msg["table"]]), use_container_width=True)

# --- 6. CORE LOGIC ---
if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)

    # Search for Airline
    target_row = None
    for _, row in df.iterrows():
        iata = str(row.get('airlines', '')).lower()
        name = str(row.get('airlines name', '')).lower()
        if iata in query or (len(name) > 3 and name in query):
            target_row = row
            break
    
    with st.chat_message("assistant"):
        if target_row is not None:
            val_text = str(target_row.get('validity', ''))
            val_score = get_date_score(val_text)
            airline_display = str(target_row.get('airlines name', '')).upper()

            # --- THE LOCKDOWN CHECK ---
            # If the user's requested date is HIGHER than the validity, we BLOCK.
            if user_score and val_score and user_score > val_score:
                reply = f"❌ **No Available Deal.**\n\nThe deals for **{airline_display}** expired on **{val_text}**. Your requested date is outside the validity."
                final_table = None # Table is HIDDEN
            else:
                cabin = next((c for c in ["bus", "eco", "first"] if c in query or (c=="bus" and "business" in query)), "eco")
                price = target_row.get(cabin, "N/A")
                reply = f"✅ Deal Found! **{airline_display}** {cabin.upper()} is **{price}** (Valid: {val_text})."
                final_table = target_row # Table is SHOWN
            
            st.write(reply)
            if final_table is not None:
                st.dataframe(pd.DataFrame([final_table]), use_container_width=True)
            
            st.session_state.messages.append({"role": "assistant", "content": reply, "table": final_table})
        else:
            st.write("I couldn't find that airline. Please try 'EY' or 'Air India'.")
