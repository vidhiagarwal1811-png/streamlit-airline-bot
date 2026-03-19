import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="Deal Finder", layout="wide")

# --- 2. DATA LOAD ---
# Using the export link for your specific sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        # High-speed CSV read
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_airline" not in st.session_state:
    st.session_state.last_airline = None

# --- 4. UI ---
st.title("✈️ Airline Deal Assistant")

# Show the full sheet as a fallback if the user wants to see everything
with st.expander("View Full Deal Sheet"):
    st.write(df)

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "table" in msg:
            st.dataframe(msg["table"])

# --- 5. SEARCH LOGIC ---
if user_input := st.chat_input("Ex: 'EY' or 'Air India'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    with st.chat_message("assistant"):
        # SEARCH ACROSS ALL COLUMNS
        # This finds the word anywhere in the sheet
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        result_df = df[mask]

        if not result_df.empty:
            response = f"I found {len(result_df)} deal(s) matching '{user_input}':"
            st.write(response)
            st.dataframe(result_df)
            # Store in history so it stays on screen
            st.session_state.messages.append({"role": "assistant", "content": response, "table": result_df})
        else:
            response = f"I couldn't find anything for '{user_input}'. Try a different airline or sector."
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
