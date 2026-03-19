import streamlit as st
import pandas as pd

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
st.title("✈️ Reliable Deal Assistant")
st.write("Search by Airline name, IATA code (EY, AI, etc.), or Cabin.")

# Display chat history (REWRITTEN to show tables from history)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data_row" in msg and msg["data_row"] is not None:
            st.dataframe(pd.DataFrame([msg["data_row"]]))

# --- 5. LOGIC ---
if user_input := st.chat_input("Ex: 'Etihad' or 'What about Business?'"):
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

    # --- STEP C: GENERATE RESPONSE ---
    with st.chat_message("assistant"):
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            airline_name = str(active_row.get('airlines name', 'UNKNOWN')).upper()
            
            if cabin:
                deal_val = active_row.get(cabin, "N/A")
                validity = active_row.get('validity', 'No data')
                reply = f"The **{cabin.upper()}** deal for **{airline_name}** is **{deal_val}**.\n\n*Validity: {validity}*"
            else:
                reply = f"I found the deals for **{airline_name}**. Which cabin (Eco, Business, First) are you looking for?"
            
            # Show the table immediately
            st.dataframe(pd.DataFrame([active_row]))
            # Save the message AND the row data to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply, 
                "data_row": active_row
            })
        else:
            reply = "I couldn't find that airline. Please check the name or IATA code (e.g., 'EY' for Etihad)."
            st.session_state.messages.append({"role": "assistant", "content": reply, "data_row": None})

        st.write(reply)
