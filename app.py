import streamlit as st
import pandas as pd
import calendar

# ✅ ADD THESE IMPORTS (NEW)
from datetime import datetime
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide")

# ✅ ADD LOGGING FUNCTION (NEW)
def log_visit():
    data = pd.DataFrame([[datetime.now()]], columns=["timestamp"])
    if os.path.exists("usage_log.csv"):
        data.to_csv("usage_log.csv", mode='a', header=False, index=False)
    else:
        data.to_csv("usage_log.csv", index=False)

# ✅ CALL LOGGING (NEW - SAFE)
try:
    log_visit()
except:
    pass

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
if user_input := st.chat_input("Ask deal (example: Airline code and Cabin type (AI deal for eco)"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    query = user_input.lower()

    # --- MONTH DETECTION ---
    month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}

    query_month = None
    for m in month_map:
        if m in query:
            query_month = month_map[m]
            break

    with st.chat_message("assistant"):

        if df.empty:
            reply = "Deal sheet could not be loaded."
            st.write(reply)

        else:

            # --- CABIN DETECTION (FIXED) ---
            words = query.replace(".", " ").split()

            cabin_column = None

            if "prem" in words or "premium" in words:
                cabin_column = "prem. eco"

            elif "bus" in words or "business" in words:
                cabin_column = "bus"

            elif "first" in words:
                cabin_column = "first"

            elif "eco" in words or "economy" in words:
                cabin_column = "eco"

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

                words = query.split()

                for _, row in df.iterrows():

                    airline = str(row["airlines"]).lower()
                    airline_name = str(row["airlines name"]).lower()
                    iata = str(row["iata"]).lower()

                    if iata in words:
                        airline_found = airline
                        filtered_df = df[df["iata"].str.lower() == iata]
                        break

                    if airline in words:
                        airline_found = airline
                        filtered_df = df[df["airlines"].str.lower() == airline]
                        break

                    if airline_name in query:
                        airline_found = airline
                        filtered_df = df[df["airlines name"].str.lower() == airline_name]
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

                        row = result.iloc[0]

                        deal_value = row[cabin_column]
                        airline_name = row["airlines name"]
                        iata_code = row["iata"]
                        validity_text = str(row.get("validity", "")).lower()

                        validity_month = None
                        for m in month_map:
                            if m in validity_text:
                                validity_month = month_map[m]
                                break

                        if query_month and validity_month and query_month > validity_month:

                            st.write("❌ No deal available for the given month.")
                            reply = "Deal not valid for the requested month."

                        else:

                            st.write(f"✈️ **{airline_name} ({iata_code})**")
                            st.write(f"💺 **{cabin_column.upper()} Deal:** {deal_value}")

                            if "validity" in result.columns:
                                st.write(f"📅 **Validity:** {row['validity']}")

                            if "exclusions" in result.columns and pd.notna(row["exclusions"]):
                                st.write(f"⚠️ **Exclusions:** {row['exclusions']}")

                            if "notes" in result.columns and pd.notna(row["notes"]):
                                st.write(f"📝 **Notes:** {row['notes']}")

                            st.write("📊 Full Deal Details:")
                            st.dataframe(result)

                            reply = f"{airline_name} {cabin_column} deal displayed."

        st.session_state.messages.append({"role": "assistant", "content": reply})
