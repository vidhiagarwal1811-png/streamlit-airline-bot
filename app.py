import streamlit as st
import pandas as pd
import re

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Smart Airline Deal Assistant Test", layout="wide", page_icon="✈️")

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

# --- 2. DATE SCORER ---
def get_date_score(text):
    if not text or pd.isna(text): return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    m_val = next((v for k, v in months.items() if k in text), 0)
    y_match = re.findall(r'\b20\d{2}\b|\b\d{2}\b', text)
    if not y_match or m_val == 0: return None
    y_str = y_match[-1]
    y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
    return (y_val * 100) + m_val

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_rows" not in st.session_state:
    st.session_state.pending_rows = None
if "last_user_score" not in st.session_state:
    st.session_state.last_user_score = None

# --- 4. DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "table" in msg and msg["table"] is not None:
            st.dataframe(msg["table"], use_container_width=True)

# --- 5. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant Test")

if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)
    if user_score:
        st.session_state.last_user_score = user_score

    # Identify Cabin
    cabin_map = {"bus": "bus", "business": "bus", "eco": "eco", "economy": "eco", "first": "first", "prem": "prem. eco"}
    found_cabin = next((v for k, v in cabin_map.items() if k in query), None)

    # Search for Airline (UPDATED: collect all matches)
    matched_rows = []
    for _, row in df.iterrows():
        iata = str(row.get('airlines', '')).lower()
        name = str(row.get('airlines name', '')).lower()
        if iata in query or (len(name) > 3 and name in query):
            matched_rows.append(row)

    with st.chat_message("assistant"):
        if not matched_rows and st.session_state.pending_rows is not None and found_cabin:
            matched_rows = st.session_state.pending_rows

        if matched_rows:
            results = []
            airline_name = ""

            for row in matched_rows:
                val_text = str(row.get('validity', ''))
                excl_text = str(row.get('exclusions', 'None listed'))
                sheet_score = get_date_score(val_text)
                airline_name = str(row.get('airlines name', '')).upper()
                active_score = user_score if user_score else st.session_state.last_user_score

                # DATE BLOCK (skip expired deals)
                if active_score and sheet_score and active_score > sheet_score:
                    continue

                if found_cabin:
                    price = row.get(found_cabin, "N/A")
                    results.append({
                        "Airline": airline_name,
                        "Cabin": found_cabin.upper(),
                        "Price": price,
                        "Validity": val_text,
                        "Exclusions": excl_text
                    })

            # CABIN NOT PROVIDED
            if not found_cabin:
                final_reply = f"I found {len(matched_rows)} deals for **{airline_name}**. Which cabin: **Economy, Business, or First?**"
                final_table = pd.DataFrame(matched_rows)
                st.session_state.pending_rows = matched_rows

            # SUCCESS
            elif results:
                final_df = pd.DataFrame(results)
                final_reply = f"✅ Found {len(results)} deals for **{airline_name}**."
                final_table = final_df
                st.session_state.pending_rows = None

            # NO VALID DEALS
            else:
                final_reply = f"❌ No valid deals found for **{airline_name}**."
                final_table = None
                st.session_state.pending_rows = None

            st.markdown(final_reply)
            if final_table is not None:
                st.dataframe(final_table, use_container_width=True)

            st.session_state.messages.append({"role": "assistant", "content": final_reply, "table": final_table})

        else:
            resp = "I couldn't find that airline. Please try 'EY' or 'AI'."
            st.write(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp, "table": None})
