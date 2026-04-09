import streamlit as st
import pandas as pd
import re
from groq import Groq  # Groq SDK

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Smart Airline Deal Assistant", layout="wide", page_icon="✈️")

DEAL_SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"
ROUTE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1h-GAtHsQA8hEnEccX1qzqQlbvu9CHauFSYTS5mgNLc0/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(DEAL_SHEET_URL)
        df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading deal sheet: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_routes():
    try:
        routes_df = pd.read_csv(ROUTE_SHEET_URL)
        routes_df.columns = routes_df.columns.astype(str).str.strip()
        return routes_df
    except Exception as e:
        st.error(f"Error loading route sheet: {e}")
        return pd.DataFrame()

df = load_data()
routes_df = load_routes()

# --- 2. DATE SCORER ---
def get_date_score(text):
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
              'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    m_val = next((v for k,v in months.items() if k in text), 0)
    y_match = re.findall(r'\b20\d{2}\b|\b\d{2}\b', text)
    if not y_match or m_val == 0:
        return None
    y_str = y_match[-1]
    y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
    return (y_val*100) + m_val

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

# ✅ FIXED FUNCTION (ONLY CHANGE)
def ask_groq(prompt):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error calling Groq API: {e}"

# --- 6. HELPER: Extract origin/destination ---
def extract_origin_destination(text):
    match = re.search(r'from (\w+) to (\w+)', text.lower())
    if match:
        return match.group(1), match.group(2)
    return None, None

# --- 7. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant")

if user_input := st.chat_input("Ex: 'AA Eco Dec 2026 from Delhi to London'"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    user_score = get_date_score(query)
    if user_score:
        st.session_state.last_user_score = user_score
    active_score = st.session_state.last_user_score or None

    # --- CABIN ---
    cabin_map = {"bus":"Bus","business":"Bus","eco":"Eco","economy":"Eco","first":"First","prem":"Prem. eco"}
    cabins_found = [v for k,v in cabin_map.items() if k in query]
    if cabins_found:
        st.session_state.last_cabins = cabins_found
    else:
        cabins_found = st.session_state.last_cabins

    # --- DIRECT FLIGHT FILTER ---
    origin, destination = extract_origin_destination(user_input)
    matched_rows = []
    airline_found = False

    if origin and destination and not routes_df.empty:
        origin = origin.lower()
        destination = destination.lower()
        direct_flights = routes_df[
            (routes_df['origin_city'].str.lower() == origin) &
            (routes_df['destination_city'].str.lower() == destination)
        ]
        if not direct_flights.empty:
            direct_airline_codes = direct_flights['direct_airlines'].str.split(',').explode().str.strip().str.lower().tolist()
            for _, row in df.iterrows():
                airline_code = str(row.get('Airlines','')).strip().lower()
                if airline_code in direct_airline_codes:
                    matched_rows.append(row)
                    airline_found = True
                    st.session_state.last_airline = {"Airlines": airline_code, "Airlines Name": row.get('Airlines Name','')}

    # --- NO DIRECT DEAL FOUND ---
    if not matched_rows:
        final_reply = f"❌ Sorry, there are no direct flights with deals from {origin.title()} to {destination.title()} in the deal sheet."
        st.markdown(final_reply)
        st.session_state.messages.append({"role":"assistant","content":final_reply,"table":None})
    else:
        # --- PROCESS DEALS ---
        results = []
        airline_display_name = ""
        for row in matched_rows:
            val_text = str(row.get('Validity',''))
            excl_text = str(row.get('Exclusions','None listed'))
            sheet_score = get_date_score(val_text)
            airline_display_name = str(row.get('Airlines Name','')).upper()
            row_dict = row.to_dict()
            row_dict["Exclusions"] = excl_text

            is_valid = True
            if active_score and (not sheet_score or sheet_score < active_score):
                is_valid = False

            if cabins_found:
                cabin_columns = ["First","Bus","Prem. eco","Eco"]
                for col in cabin_columns:
                    if col not in cabins_found:
                        row_dict.pop(col,None)
                for cabin in cabins_found:
                    if cabin in row_dict:
                        val = row_dict.pop(cabin)
                        row_dict.pop(cabin.upper(),None)
                        row_dict[cabin.upper()] = val

            if is_valid:
                results.append(row_dict)

        final_df = pd.DataFrame(results)
        base_cols = ["Airlines","Airlines Name","IATA"] + ([c.upper() for c in cabins_found] if cabins_found else []) + ["Validity","Exclusions"]
        remaining_cols = [c for c in final_df.columns if c not in set(base_cols) and c != "S.No"]
        final_df = final_df.reindex(columns=base_cols + remaining_cols)

        final_reply = f"✅ Found {len(results)} valid deal(s) for **{airline_display_name}**."
        final_table = final_df

        # --- AI SUMMARY ---
        rows_text = final_df.to_string(index=False)
        prompt = f"""
Customer asked: '{user_input}'
Here are the deals from the sheet (keep all O/B and I/B as-is, do not replace or explain):
{rows_text}

Please summarize the deals in simple language, highlight important notes/exclusions, use the word 'deal' only, and be concise.
"""
        ai_summary = ask_groq(prompt)

        st.markdown(final_reply)
        st.markdown(f"**AI Summary:** {ai_summary}")

        if final_table is not None and not final_table.empty:
            final_table = final_table.copy()
            final_table.columns = final_table.columns.astype(str).str.strip()
            final_table = final_table.loc[:, ~final_table.columns.duplicated()]
            st.dataframe(final_table, use_container_width=True)

        st.session_state.messages.append({"role":"assistant","content":final_reply,"table":final_table})
