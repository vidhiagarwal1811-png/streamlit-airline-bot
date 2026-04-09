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

def ask_groq(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-20b"
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling Groq API: {e}"

# --- 6. CHAT LOGIC ---
st.title("✈️ Smart Airline Deal Assistant")

user_input = st.chat_input("Ex: 'AA Eco Dec 2026' or calculate margin")
if user_input:

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    # --- Margin Calculation ---
    if "calculate margin" in user_input.lower():
        st.info("⚠️ Use Python to calculate margins. AI will not calculate them accurately.")
        base_fare = st.number_input("Base Fare", min_value=0, value=2500)
        yq = st.number_input("YQ/Taxes", min_value=0, value=5000)
        selling_price = st.number_input("Selling Price", min_value=0, value=10000)
        margin = selling_price - (base_fare + yq)
        st.success(f"Margin for First Class: {margin}")
    else:
        query = user_input.lower().strip()
        user_score = get_date_score(query)

        if user_score:
            st.session_state.last_user_score = user_score
        active_score = st.session_state.last_user_score or None

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

        if not airline_found and st.session_state.last_airline is not None:
            last_code = st.session_state.last_airline["Airlines"]
            last_name = st.session_state.last_airline["Airlines Name"]
            for _, row in df.iterrows():
                airline_code = str(row.get('Airlines', '')).strip().lower()
                airline_name = str(row.get('Airlines Name', '')).strip().lower()
                if airline_code == last_code or airline_name == last_name:
                    matched_rows.append(row)

        with st.chat_message("assistant"):

            if not matched_rows and st.session_state.pending_rows is not None:
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
                    row_dict = row.to_dict()
                    row_dict["Exclusions"] = excl_text

                    is_valid = True
                    if active_score:
                        if not sheet_score or sheet_score < active_score:
                            is_valid = False

                    if cabins_found:
                        for col in ["First","Bus","Prem. eco","Eco"]:
                            if col not in cabins_found and col in row_dict:
                                row_dict.pop(col, None)

                    if is_valid:
                        results.append(row_dict)

                if results:
                    final_df = pd.DataFrame(results)
                    base_cols = ["Airlines", "Airlines Name", "IATA"] + \
                                ([c for c in cabins_found] if cabins_found else []) + \
                                ["Validity", "Exclusions"]
                    remaining_cols = [c for c in final_df.columns if c not in set(base_cols) and c != "S.No"]
                    final_df = final_df.reindex(columns=base_cols + remaining_cols)
                    final_reply = f"✅ Found {len(results)} valid deal(s) for **{airline_display_name}**."
                    final_table = final_df

                    # AI summary (literal table only)
                    rows_text = final_df.to_csv(index=False)
                    prompt = (
                        f"Customer asked: '{user_input}'\n\n"
                        "Summarize the airline **deals** from the table below.\n"
                        "Keep all fare/cabin codes exactly as in the sheet.\n"
                        "Use the word 'deals', not 'discounts'.\n"
                        "Highlight validity and exclusions. Make it concise and readable.\n"
                        "Table (CSV literal):\n'''\n"
                        + rows_text + "'''\n"
                    )
                    ai_summary = ask_groq(prompt)

                else:
                    final_reply = f"❌ No deals found for **{airline_display_name}**."
                    final_table = None
                    ai_summary = "No deals to summarize."

                st.markdown(final_reply)
                st.markdown(f"**AI Summary:** {ai_summary}")

                if final_table is not None and not final_table.empty:
                    final_table.columns = final_table.columns.astype(str).str.strip()
                    final_table = final_table.loc[:, ~final_table.columns.duplicated()]
                    st.dataframe(final_table, use_container_width=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_reply,
                    "table": final_table
                })

            else:
                resp = "I couldn't find that airline. Please try 'AI', 'AA', etc."
                st.write(resp)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resp,
                    "table": None
                })
