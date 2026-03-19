import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(page_title="Strict Deal Assistant", layout="wide", page_icon="✈️")

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

# --- 3. THE DATE COMPARATOR ---
def get_date_score(text):
    """Converts 'Dec 2026' or '31 Mar 26' into YYYYMM (e.g., 202612)."""
    if not text or pd.isna(text): return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    
    found_m = next((v for k, v in months.items() if k in text), None)
    year_match = re.search(r'(20\d{2})|(\d{2})$|(\d{2})\s', text)
    
    if year_match and found_m:
        y_str = year_match.group().strip().replace("'", "")
        found_y = int(y_str) if len(y_str) == 4 else int("20" + y_str)
        return (found_y * 100) + found_m
    return None

# --- 4. SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "current_airline" not in st.session_state: st.session_state.current_airline = None

# --- 5. UI ---
st.title("✈️ Airline Deal Assistant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(pd.DataFrame([msg["data"]]), use_container_width=True)

# --- 6. LOGIC ---
if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.write(user_input)

    query = user_input.lower().strip()
    req_score = get_date_score(query)

    # Find Airline
    found_row = None
    for _, row in df.iterrows():
        if str(row.get('airlines','')).lower() in query or str(row.get('airlines name','')).lower() in query:
            found_row = row
            st.session_state.current_airline = row
            break
    
    with st.chat_message("assistant"):
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            val_str = str(active_row.get('validity', ''))
            val_score = get_date_score(val_str)
            airline_name = str(active_row.get('airlines name', '')).upper()

            # --- THE CRITICAL CHECK ---
            if req_score and val_score and req_score > val_score:
                response = f"❌ **No Available Deal for these dates.**\n\nThe deal for **{airline_name}** expired on **{val_str}**. Your request for {user_input.split()[-2:]} is not valid."
                display_data = None # This ensures the table is HIDDEN
            else:
                cabin = next((c for c in ["bus", "eco", "first"] if c in query or (c=="bus" and "business" in query)), "eco")
                price = active_row.get(cabin, "N/A")
                response = f"✅ Deal Found! **{airline_name}** {cabin.upper()} is **{price}** (Valid: {val_str})."
                display_data = active_row # This shows the table
            
            st.write(response)
            if display_data is not None: st.dataframe(pd.DataFrame([display_data]), use_container_width=True)
            st.session_state.messages.append({"role": "assistant", "content": response, "data": display_data})
        else:
            st.write("Airline not found.")
