import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="Airline Deal Bot", layout="wide", page_icon="✈️")

# --- 2. DATA LOAD ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        # Clean column names for easier searching
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Could not connect to Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_found_df" not in st.session_state:
    st.session_state.last_found_df = None

# --- 4. UI ---
st.title("✈️ Airline Deal Assistant (Live Data)")
st.info("Search by Airline (e.g., 'Etihad'), IATA (e.g., 'EY'), or Destination.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        # If the assistant message has data attached, show the table again
        if msg["role"] == "assistant" and "data" in msg:
            st.dataframe(msg["data"], use_container_width=True)

# --- 5. SEARCH LOGIC ---
if user_input := st.chat_input("Ex: 'Show me Air India deals' or 'What about Business class?'"):
    # Store User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    with st.chat_message("assistant"):
        # SEARCH STEP: Check if user input matches any cell in the sheet
        # This searches across ALL columns (Airline, Sector, Cabin, etc.)
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        found_df = df[mask]

        # MEMORY STEP: If no NEW results found, but we have a previous search, use that
        if found_df.empty and st.session_state.last_found_df is not None:
            # Check if user is asking for a specific cabin within the previous results
            if any(x in query for x in ["bus", "eco", "first", "prem"]):
                found_df = st.session_state.last_found_df
                response_text = f"Filtering the previous results for your request: '{user_input}'"
            else:
                response_text = "I couldn't find a new match. Here is the last airline we discussed:"
                found_df = st.session_state.last_found_df
        elif not found_df.empty:
            response_text = f"I found {len(found_df)} matching deal(s) for '{user_input}':"
            st.session_state.last_found_df = found_df
        else:
            response_text = "I'm sorry, I couldn't find any deals matching that search. Please try an airline name or IATA code."
            found_df = None

        # DISPLAY STEP
        st.write(response_text)
        if found_df is not None:
            st.dataframe(found_df, use_container_width=True)
            
        # SAVE TO HISTORY
        history_entry = {"role": "assistant", "content": response_text}
        if found_df is not None:
            history_entry["data"] = found_df
        st.session_state.messages.append(history_entry)
