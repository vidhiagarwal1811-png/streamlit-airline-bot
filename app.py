import streamlit as st
import pandas as pd
import re

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Strict Deal Bot with Memory", layout="wide", page_icon="✈️")

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

# --- 2. THE DATE SCORER (THE BRAINS) ---
def get_date_score(text):
    """Converts 'Dec 2026' or '31 MAR 26' into a number like 202612."""
    if not text or pd.isna(text): return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    
    # Find Month
    m_val = next((v for k, v in months.items() if k in text), 0)
    
    # Find Year
    y_match = re.findall(r'\b20\d{2}\b|\b\d{2}\b', text)
    if not y_match or m_val == 0: return None
    
    y_str = y_match[-1]
    y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
    return (y_val * 100) + m_val

# --- 3. INITIALIZE SESSION STATE (MEMORY) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. DISPLAY CHAT HISTORY ---
# This part ensures the memory is visible on the screen
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "table" in msg and msg["table"] is not None:
            st.dataframe(pd.DataFrame([msg["table"]]), use_container_width=True)

# --- 5. NEW MESSAGE LOGIC ---
if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    # Add User Message to Memory
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)

    # Find Airline
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
            sheet_score = get_date_score(val_text)
            airline_name = str(target_row.get('airlines name', '')).upper()

            # --- THE LOCKDOWN ---
            if user_score and sheet_score and user_score > sheet_score:
                final_reply = f"❌ **No Available Deal.**\n\nThe deals for **{airline_name}** are only valid until **{val_text}**. Your requested travel date is past this period."
                final_table = None
            else:
                cabin = next((c for c in ["bus", "eco", "first"] if c in query or (c=="bus" and "business" in query)), "eco")
                price = target_row.get(cabin, "N/A")
                final_reply = f"✅ Deal Found! **{airline_name}** {cabin.upper()} is **{price}** (Valid: {val_text})."
                final_table = target_row
            
            # Display and Save Assistant Response
            st.write(final_reply)
            if final_table is not None:
                st.dataframe(pd.DataFrame([final_table]), use_container_width=True)
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": final_reply, 
                "table": final_table
            })
        else:
            resp = "I couldn't find that airline. Please try 'EY' or 'Air India'."
            st.write(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp, "table": None})
