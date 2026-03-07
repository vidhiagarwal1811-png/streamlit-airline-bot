import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- GOOGLE SHEET URL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame()

df = load_sheet(SHEET_URL)

# --- APP TITLE ---
st.title("✈️ Live Deal Sheet Assistant")

# --- SHOW CHAT HISTORY ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- USER INPUT ---
if user_input := st.chat_input("Ask airline deals (example: emirates business / cheapest eco)"):

    st.session_state.messages.append({"role": "user", "content": user_input})

    query = user_input.lower()

    with st.chat_message("assistant"):

        if df.empty:
            reply = "Deal sheet could not be loaded."
            st.write(reply)

        else:

            # --- CHEAPEST DEAL LOGIC ---
            if "cheapest" in query or "best" in query:

                cabin_map = {
                    "eco": "eco",
                    "economy": "eco",
                    "prem": "prem.eco",
                    "premium": "prem.eco",
                    "bus": "bus",
                    "business": "bus",
                    "first": "first"
                }

                cabin_column = None

                for key in cabin_map:
                    if key in query:
                        cabin_column = cabin_map[key]
                        break

                if cabin_column and cabin_column in df.columns:

                    best_deals = df.sort_values(by=cabin_column).head(5)

                    reply = f"Top {cabin_column} deals:"
                    st.write(reply)
                    st.dataframe(best_deals[["airlines", cabin_column]])

                else:
                    reply = "Please specify cabin class: Eco / Prem.Eco / Bus / First"
                    st.write(reply)

            else:

                # --- AIRLINE DETECTION ---
                filtered_df = df.copy()
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
                    "business": "bus",
                    "bus": "bus",
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

                # --- OUTPUT ---
                if airline_found and cabin_column and cabin_column in filtered_df.columns:

                    result = filtered_df[["airlines", cabin_column]]

                    reply = f"{airline_found.title()} {cabin_column} deal:"
                    st.write(reply)
                    st.dataframe(result)

                elif airline_found:
                    reply = "Please specify cabin class: Eco / Prem.Eco / Bus / First"
                    st.write(reply)

                else:
                    reply = "Please mention a valid airline name."
                    st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
