import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Bot", layout="wide")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_sheet(SHEET_URL)

# --- UI ---
st.title("Live Deal Sheet Assistant ✈️")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- USER INPUT ---
if user_input := st.chat_input("Ask for airline deals..."):

    st.session_state.messages.append({"role": "user", "content": user_input})

    query = user_input.lower()
    filtered_df = df.copy()

    with st.chat_message("assistant"):

        # --- AIRLINE DETECTION ---
        airline_found = None

        for airline in df["airlines"].str.lower().unique():
            if airline in query:
                airline_found = airline
                break

        if airline_found:
            filtered_df = filtered_df[
                filtered_df["airlines"].str.lower() == airline_found
            ]

        # --- CABIN DETECTION ---
        cabin_map = {
            "first": "first",
            "bus": "bus",
            "business": "bus",
            "prem": "prem.eco",
            "premium": "prem.eco",
            "eco": "eco",
            "economy": "eco"
        }

        cabin_column = None
        for key in cabin_map:
            if key in query:
                cabin_column = cabin_map[key]
                break

        # --- RESULT OUTPUT ---
        if filtered_df.empty:
            reply = "No deals found for that airline."

        else:
            if cabin_column and cabin_column in filtered_df.columns:
                result = filtered_df[["airlines", cabin_column]]
            else:
                result = filtered_df

            reply = "Here are the matching deals:"
            st.write(reply)
            st.dataframe(result)

        st.session_state.messages.append({"role": "assistant", "content": reply})
