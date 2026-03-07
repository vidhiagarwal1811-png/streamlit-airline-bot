import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide")

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

# --- TITLE ---
st.title("✈️ Smart Airline Deal Assistant")

# --- SHOW CHAT HISTORY ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- USER INPUT ---
if user_input := st.chat_input("Ask deal (example: LH business / cheapest eco deal)"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    query = user_input.lower()

    with st.chat_message("assistant"):

        if df.empty:
            reply = "Deal sheet could not be loaded."
            st.write(reply)

        else:

            # --- CABIN DETECTION ---
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

            # --- CHEAPEST DEAL LOGIC ---
            if "cheapest" in query or "best" in query:

                if cabin_column and cabin_column in df.columns:

                    best_deals = df.sort_values(by=cabin_column).head(5)

                    st.write(f"🏆 Top {cabin_column} deals:")
                    st.dataframe(best_deals)

                    reply = f"Showing best {cabin_column} deals."

                else:
                    reply = "Please specify cabin class: Eco / Prem.Eco / Bus / First"
                    st.write(reply)

            else:

                filtered_df = df.copy()

                airline_found = None

                for _, row in df.iterrows():

                    airline = str(row["airlines"]).lower()
                    iata = str(row["iata"]).lower()

                    if airline in query or iata in query:
                        airline_found = airline
                        filtered_df = df[df["airlines"].str.lower() == airline]
                        break

                if not airline_found:
                    reply = "Please mention a valid airline name or IATA code."
                    st.write(reply)

                elif not cabin_column:
                    reply = "Please specify cabin class: Eco / Prem.Eco / Bus / First."
                    st.write(reply)

                else:

                    result = filtered_df

                    if result.empty:
                        reply = "No deal found."
                        st.write(reply)

                    else:

                        deal_value = result.iloc[0][cabin_column]
                        airline_name = result.iloc[0]["airlines"]
                        iata_code = result.iloc[0]["iata"]

                        # --- TEXT RESPONSE ---
                        st.write(f"✈️ **{airline_name} ({iata_code})**")
                        st.write(f"💺 **{cabin_column.upper()} Deal:** {deal_value}")

                        if "exclusions" in result.columns:
                            st.write(f"⚠️ **Exclusions:** {result.iloc[0]['exclusions']}")

                        if "notes" in result.columns:
                            st.write(f"📝 **Notes:** {result.iloc[0]['notes']}")

                        # --- FULL ROW TABLE ---
                        st.write("📊 Full Deal Details:")
                        st.dataframe(result)

                        reply = f"{airline_name} {cabin_column} deal displayed."

        st.session_state.messages.append({"role": "assistant", "content": reply})
