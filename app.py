import streamlit as st
import pandas as pd
import re

# --- 1. SETUP ---
st.set_page_config(page_title="Deal Finder", layout="wide", page_icon="✈️")

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

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_airline" not in st.session_state:
    st.session_state.current_airline = None

# --- 4. UI ---
st.title("✈️ Smart Deal Assistant")
st.write("Search by Airline, Cabin, and Travel Date (e.g., 'Air India Business 2027').")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data_row" in msg and msg["data_row"] is not None:
            st.dataframe(pd.DataFrame([msg["data_row"]]))

# --- 5. LOGIC ---
if user_input := st.chat_input("Ex: 'EY Business March 2027'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    # --- STEP A: IDENTIFY AIRLINE ---
    found_row = None
    for _, row in df.iterrows():
        name = str(row.get('airlines name', '')).lower()
        iata = str(row.get('airlines', '')).lower()
        if iata in query or name in query:
            st.session_state.current_airline = row
            found_row = row
            break
            
    # --- STEP B: IDENTIFY CABIN ---
    cabin = None
    if any(x in query for x in ["bus", "business"]): cabin = "bus"
    elif any(x in query for x in ["eco", "economy"]): cabin = "eco"
    elif any(x in query for x in ["prem", "premium"]): cabin = "prem. eco"
    elif "first" in query: cabin = "first"

    # --- STEP C: DATE VALIDATION LOGIC ---
    # Extract year from user input (e.g., 2026, 2027)
    user_year_match = re.search(r'20\d{2}', query)
    user_year = int(user_year_match.group()) if user_year_match else None

    # --- STEP D: GENERATE RESPONSE ---
    with st.chat_message("assistant"):
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            airline_name = str(active_row.get('airlines name', 'UNKNOWN')).upper()
            validity_text = str(active_row.get('validity', '')).lower()
            
            # Extract year from the sheet's validity column
            sheet_year_match = re.search(r'20\d{2}', validity_text)
            sheet_year = int(sheet_year_match.group()) if sheet_year_match else 2026 # Default to 2026 if not found

            # Check if Travel Date is expired
            if user_year and user_year > sheet_year:
                reply = f"❌ **No Available Deal.** The current deals for **{airline_name}** are only valid until **{active_row.get('validity')}**. Your requested travel date in {user_year} is beyond this period."
                display_row = None # Don't show the row if it's not applicable
            else:
                if cabin:
                    deal_val = active_row.get(cabin, "N/A")
                    reply = f"✅ Deal Found! The **{cabin.upper()}** deal for **{airline_name}** is **{deal_val}**.\n\n*Validity: {active_row.get('validity')}*"
                else:
                    reply = f"I found the deals for **{airline_name}** (Valid until {active_row.get('validity')}). Which cabin are you looking for?"
                display_row = active_row
            
            if display_row is not None:
                st.dataframe(pd.DataFrame([display_row]))
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply, 
                "data_row": display_row
            })
        else:
            reply = "I couldn't find that airline. Please check the name or IATA code (e.g., 'EY' for Etihad)."
            st.session_state.messages.append({"role": "assistant", "content": reply, "data_row": None})

        st.write(reply)
