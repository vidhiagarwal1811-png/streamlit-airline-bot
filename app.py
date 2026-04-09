import streamlit as st
import pandas as pd
import re
from groq import Groq  # <-- Groq API client

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Smart Airline Deal Assistant", layout="wide", page_icon="✈️")

# Initialize Groq client using Streamlit Secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

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

# --- 5. HELPER FUNCTION: Ask Groq AI ---
def ask_groq(prompt):
    """
    Sends a prompt to Groq AI and returns the AI-generated response.
    """
    try:
        response = client.predict(prompt)  # Adjust based on your Groq SDK method
        return response
    except Exception as e:
        return f"Error calling Groq API: {e}"

# --- 6. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant")

if user_input := st.chat_input("Ex: 'AA Eco Dec 2026'"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)

    # --- DATE MEMORY ---
    if user_score:
        st.session_state.last_user_score = user_score
    active_score = st.session_state.last_user_score or None

    # --- CABIN MEMORY ---
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

    # --- AIRLINE SEARCH ---
    matched_rows = []
    airline_found = False
    for _, row in df.iterrows():
        airline_code = str(row.get('Airlines', '')).strip().lower()
        airline_name = str(row.get('Airlines Name', '')).strip().lower()
        if airline_code in query or airline_name in query:
            matched_rows.append(row)
            airline_found = True
            st.session_state.last_airline = {
                "Airlines": airline_code,
                "Airlines Name": airline_name
            }

    # --- FALLBACK AIRLINE CONTEXT ---
    if not airline_found and st.session_state.last_airline is not None:
        last_code = st.session_state.last_airline["Airlines"]
        last_name = st.session_state.last_airline["Airlines Name"]
        for _, row in df.iterrows():
            airline_code = str(row.get('Airlines', '')).strip().lower()
            airline_name = str(row.get('Airlines Name', '')).strip().lower()
            if airline_code == last_code or airline_name == last_name:
                matched_rows.append(row)

    # --- ASSISTANT RESPONSE ---
    with st.chat_message("assistant"):

        if not matched_rows and st.session_state.pending_rows is not None:
            matched_rows = st.session_state.pending_rows

        if matched_rows:
            # Keep pending rows if cabin not specified
            if not cabins_found:
                st.session_state.pending_rows = matched_rows
            else:
                st.session_state.pending_rows = None

            # Prepare rows for AI summarization
            filtered_rows = []
            for row in matched_rows:
                val_text = str(row.get('Validity', ''))
                sheet_score = get_date_score(val_text)
                is_valid = True
                if active_score:
                    if not sheet_score or sheet_score < active_score:
                        is_valid = False
                if is_valid:
                    filtered_rows.append(row)

            if filtered_rows:
                final_df = pd.DataFrame(filtered_rows)
                # Prepare readable text for Groq AI
                rows_text = "\n".join([
                    f"{r['Airlines']} {r['Airlines Name']} - Eco: {r.get('Eco','-')}, Bus: {r.get('Bus','-')}, First: {r.get('First','-')}, Validity: {r.get('Validity','-')}, Notes: {r.get('Exclusions','None')}"
                    for _, r in final_df.iterrows()
                ])
                # AI prompt
                prompt = f"""
                You are an airline deals assistant. A customer asked: '{user_input}'
                Here are the deals from the spreadsheet:

                {rows_text}

                Please:
                1. Summarize the deals in simple, clear language for the customer.
                2. Highlight important notes or exclusions they should know.
                3. Keep it concise and friendly.
                """
                ai_summary = ask_groq(prompt)

                st.markdown(f"**AI Summary:** {ai_summary}")
                st.dataframe(final_df, use_container_width=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ai_summary,
                    "table": final_df
                })
            else:
                st.markdown("❌ No valid deals found for the requested date/cabin.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "No valid deals found",
                    "table": None
                })

        else:
            resp = "I couldn't find that airline. Please try 'AA', 'AI', etc."
            st.write(resp)
            st.session_state.messages.append({
                "role": "assistant",
                "content": resp,
                "table": None
            })
