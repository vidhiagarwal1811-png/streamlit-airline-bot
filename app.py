import streamlit as st
import pandas as pd
import re
from groq import Groq  # Groq SDK

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Smart Airline Deal Assistant", layout="wide", page_icon="✈️")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 2. DATE SCORER ---
def get_date_score(text):
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
              'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    m_val = next((v for k, v in months.items() if k in text), 0)
    y_match = re.findall(r'\b20\d{2}\b|\b\d{2}\b', text)
    if not y_match or m_val == 0:
        return None
    y_str = y_match[-1]
    y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
    return (y_val * 100) + m_val

# --- 3. SESSION STATE ---
for key in ["messages", "pending_rows", "last_user_score", "last_cabins", "last_airline"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "messages" else []

# --- 4. DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "table" in msg and msg["table"] is not None:
            table = msg["table"].copy()
            table.columns = table.columns.astype(str).str.strip()
            table = table.loc[:, ~table.columns.duplicated()]
            st.dataframe(table, use_container_width=True)

# --- 5. INITIALIZE GROQ CLIENT ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def ask_groq(prompt):
    try:
        response = client.predict(prompt)  # Use latest Groq SDK
        return response.text
    except Exception as e:
        return f"Error calling Groq API: {e}"

# --- 6. PARSE ORIGIN/DESTINATION ---
def parse_origin_destination(text):
    match = re.search(r'from\s+(\w+)\s+to\s+(\w+)', text.lower())
    if match:
        return match.group(1), match.group(2)
    return None, None

# --- 7. GET DIRECT FLIGHT AIRLINES ---
def get_direct_flight_airlines(user_input, airlines_list):
    origin, dest = parse_origin_destination(user_input)
    if not origin or not dest:
        return []
    prompt = f"""
User wants a direct flight from {origin.upper()} to {dest.upper()}.
Here is a list of airlines from the deal sheet:
{', '.join([a['Airlines Name'] for a in airlines_list])}

Return ONLY airlines that you are certain operate a DIRECT (non-stop) flight
between {origin.upper()} and {dest.upper()}. Do NOT guess. If unsure, return empty.

Output: a comma-separated list of airline names.
"""
    response = ask_groq(prompt)
    airlines = [a.strip().lower() for a in response.split(',') if a.strip()]
    return airlines

# --- 8. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant")

if user_input := st.chat_input("Ex: 'AA Eco Dec 2026' or 'I want to fly from Kolkata to London'"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)

    # --- DATE MEMORY ---
    if user_score:
        st.session_state.last_user_score = user_score
    active_score = st.session_state.last_user_score or None

    # --- CABIN ---
    cabin_map = {
        "bus": "Bus", "business": "Bus",
        "eco": "Eco", "economy": "Eco",
        "first": "First", "prem": "Prem. eco"
    }
    cabins_found = [v for k, v in cabin_map.items() if k in query]
    if cabins_found:
        st.session_state.last_cabins = cabins_found
    else:
        cabins_found = st.session_state.last_cabins

    # --- AIRLINE SEARCH & DIRECT FILTER ---
    airlines_list = df.to_dict(orient="records")
    direct_airlines = get_direct_flight_airlines(user_input, airlines_list)

    if direct_airlines:
        matched_rows = [
            row for row in airlines_list
            if row.get('Airlines Name', '').strip().lower() in direct_airlines
        ]
    else:
        matched_rows = []

    # --- ASSISTANT BLOCK ---
    with st.chat_message("assistant"):

        if not matched_rows:
            resp = "❌ No direct flight deals available in the deal sheet."
            st.write(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp, "table": None})
        else:
            results = []
            airline_display_name = ""
            for row in matched_rows:
                val_text = str(row.get('Validity', ''))
                excl_text = str(row.get('Exclusions', 'None listed'))
                sheet_score = get_date_score(val_text)
                airline_display_name = str(row.get('Airlines Name', '')).upper()
                row_dict = row.copy()
                row_dict["Exclusions"] = excl_text

                # --- DATE FILTER ---
                is_valid = True
                if active_score:
                    if not sheet_score or sheet_score < active_score:
                        is_valid = False

                # --- CABIN FILTER ---
                if cabins_found:
                    cabin_columns = ["First", "Bus", "Prem. eco", "Eco"]
                    for col in cabin_columns:
                        if col not in cabins_found:
                            row_dict.pop(col, None)
                    for cabin in cabins_found:
                        if cabin in row_dict:
                            val = row_dict.pop(cabin)
                            row_dict[cabin.upper()] = val

                if is_valid:
                    results.append(row_dict)

            final_df = pd.DataFrame(results)
            final_df = final_df.loc[:, ~final_df.columns.duplicated()]
            final_reply = f"✅ Found {len(results)} valid direct-flight deal(s) for **{airline_display_name}**."

            # --- GENERATE AI SUMMARY ---
            rows_text = final_df.to_string(index=False)
            prompt = f"""
Customer asked: '{user_input}'

Here are the deals from the sheet. Keep the deal format as-is.
Do NOT change O/B, I/B, B+YQ, or any deal codes.
Do NOT use the word 'discount'. Only refer to deals.
Keep spacing and formatting neat.

{rows_text}
"""
            ai_summary = ask_groq(prompt)

            # --- DISPLAY ---
            st.markdown(final_reply)
            st.markdown(f"**AI Summary:**\n{ai_summary}")

            if not final_df.empty:
                st.dataframe(final_df, use_container_width=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": final_reply,
                "table": final_df
            })
