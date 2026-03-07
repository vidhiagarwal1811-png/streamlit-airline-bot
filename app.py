import streamlit as st
import pandas as pd

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Bot", layout="wide")

# --- 2. INITIALIZE CHAT STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. CONNECT TO GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Failed to load Google Sheet: {e}")
        return pd.DataFrame()

df = load_sheet(SHEET_URL)

# --- 4. APP UI ---
st.title("Live Deal Sheet Assistant ✈️")

# Show previous chat messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- 5. USER INPUT ---
if user_input := st.chat_input("Enter Airline Name to check deals..."):

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):

        if df.empty:
            reply = "Deal sheet is not available right now."
        else:
            results = df[df.astype(str).apply(lambda row: row.str.contains(user_input, case=False).any(), axis=1)]

            if results.empty:
                reply = "No deals found for this airline."
            else:
                reply = "Here are the available deals:"
                st.write(reply)
                st.dataframe(results)

        st.session_state.messages.append({"role": "assistant", "content": reply})
