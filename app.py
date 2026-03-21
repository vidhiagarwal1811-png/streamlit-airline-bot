import streamlit as st
import pandas as pd
import re
import openai
import json

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Smart Airline Deal Assistant Test", layout="wide", page_icon="✈️")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 2. DATE SCORER ---
def get_date_score(text):
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
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

# --- 4. OPENAI API SETUP ---
openai.api_key = st.secrets.get("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", "")

def query_gen_ai(prompt: str):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"Gen AI error: {e}")
        return None

# --- 5. DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "table" in msg and msg["table"] is not None:
            st.dataframe(msg["table"], use_container_width=True)

# --- 6. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant Test (Gen AI Enhanced)")

if user_input := st.chat_input("Ex: 'Show me business and economy deals for Air Canada in Dec 2026'"):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # --- 6A. Use Gen AI to extract airline, cabins, date ---
    structured_prompt = (
        f"Extract airline code or name, cabins, and travel date from this query:\n'{user_input}'\n"
        "Return as JSON with keys: airline, cabins (list), date."
    )
    gen_ai_output = query_gen_ai(structured_prompt)
    airline_query, cabins_found, user_date = None, [], None

    if gen_ai_output:
        try:
            structured_data = json.loads(gen_ai_output)
            airline_query = structured_data.get("airline")
            cabins_found = structured_data.get("cabins", [])
            user_date = structured_data.get("date")
        except:
            st.warning("Could not parse AI response. Falling back to regex parsing.")
            airline_query = user_input
            cabins_found = []
            user_date = None
    else:
        airline_query = user_input

    # --- 6B. Update session date if provided ---
    user_score = get_date_score(user_date)
    if user_score:
        st.session_state.last_user_score = user_score
    active_score = st.session_state.last_user_score

    # --- 6C. Cabin memory ---
    cabin_map = {"bus": "Bus", "business": "Bus", "eco": "Eco", "economy": "Eco",
                 "first": "First", "prem": "Prem. eco"}
    if cabins_found:
        st.session_state.last_cabins = [cabin_map.get(c.lower(), c) for c in cabins_found]
    else:
        cabins_found = st.session_state.last_cabins

    # --- 6D. Airline reset if changed ---
    current_airline_in_query = None
    for _, row in df.iterrows():
        airline_code = str(row.get('Airlines', '')).strip().lower()
        airline_name = str(row.get('Airlines Name', '')).strip().lower()
        if airline_query and (airline_code in airline_query.lower() or airline_name in airline_query.lower()):
            current_airline_in_query = {"Airlines": airline_code, "Airlines Name": airline_name}
            break

    if st.session_state.last_airline and current_airline_in_query:
        if (current_airline_in_query["Airlines"] != st.session_state.last_airline["Airlines"] or
            current_airline_in_query["Airlines Name"] != st.session_state.last_airline["Airlines Name"]):
            st.session_state.last_user_score = None
            st.session_state.last_cabins = None
            st.session_state.pending_rows = None
            st.session_state.last_airline = current_airline_in_query
    elif current_airline_in_query:
        st.session_state.last_airline = current_airline_in_query

    # --- 6E. Search matching rows ---
    matched_rows = []
    airline_found = False
    for _, row in df.iterrows():
        airline_code = str(row.get('Airlines', '')).strip().lower()
        airline_name = str(row.get('Airlines Name', '')).strip().lower()
        if airline_query and (airline_code in airline_query.lower() or airline_name in airline_query.lower()):
            matched_rows.append(row)
            airline_found = True
            st.session_state.last_airline = {"Airlines": airline_code, "Airlines Name": airline_name}

    if not airline_found and st.session_state.last_airline:
        last_code = st.session_state.last_airline["Airlines"]
        last_name = st.session_state.last_airline["Airlines Name"]
        for _, row in df.iterrows():
            airline_code = str(row.get('Airlines', '')).strip().lower()
            airline_name = str(row.get('Airlines Name', '')).strip().lower()
            if airline_code == last_code or airline_name == last_name:
                matched_rows.append(row)

    with st.chat_message("assistant"):

        if not matched_rows and st.session_state.pending_rows:
            matched_rows = st.session_state.pending_rows

        if matched_rows:
            if not cabins_found:
                st.session_state.pending_rows = matched_rows
            else:
                st.session_state.pending_rows = None

            results = []
            airline_display_name = ""

            for row in matched_rows:
                val_text = str(row.get('Validity', ''))
                excl_text = str(row.get('Exclusions', 'None listed'))
                sheet_score = get_date_score(val_text)
                airline_display_name = str(row.get('Airlines Name', '')).upper()

                if active_score and sheet_score and active_score > sheet_score:
                    continue

                if cabins_found:
                    row_dict = row.to_dict()
                    row_dict["Exclusions"] = excl_text
                    cabin_columns = ["First", "Bus", "Prem. eco", "Eco"]
                    for col in cabin_columns:
                        if col not in cabins_found:
                            row_dict.pop(col, None)
                    for cabin in cabins_found:
                        if cabin in row_dict:
                            row_dict[cabin.upper()] = row_dict.pop(cabin)
                    results.append(row_dict)

            if not cabins_found:
                final_reply = f"I found {len(matched_rows)} deals for **{airline_display_name}**. Which cabin(s): **Economy, Business, or First?**"
                final_table = pd.DataFrame(matched_rows)
            elif results:
                final_df = pd.DataFrame(results)
                base_cols = ["Airlines", "Airlines Name", "IATA"] + [c.upper() for c in cabins_found] + ["Validity", "Exclusions"]
                remaining_cols = [c for c in final_df.columns if c not in base_cols and c != "S.No"]
                final_df = final_df[base_cols + remaining_cols]
                final_reply = f"✅ Found {len(results)} deal entries for **{airline_display_name}**."
                final_table = final_df
            else:
                final_reply = f"❌ No valid deals found for **{airline_display_name}**."
                final_table = None

            st.markdown(final_reply)
            if final_table is not None:
                st.dataframe(final_table, use_container_width=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": final_reply,
                "table": final_table
            })
        else:
            resp = "I couldn't find that airline. Please try 'AA' or 'AC'."
            st.write(resp)
            st.session_state.messages.append({
                "role": "assistant",
                "content": resp,
                "table": None
            })
