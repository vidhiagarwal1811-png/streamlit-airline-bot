import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETTINGS ---
st.set_page_config(page_title="Airline Deal Bot", layout="wide")

# --- 2. THE BRAIN (GEMINI) ---
# We wrap this in a try/except so even if the key is wrong, the app doesn't crash
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        ai_available = True
    else:
        ai_available = False
except:
    ai_available = False

# --- 3. THE DATA (GOOGLE SHEET) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Cannot read Google Sheet. Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. UI ---
st.title("✈️ Airline Deal Assistant")

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. MAIN CHAT LOGIC ---
if user_input := st.chat_input("Ask for a deal (e.g., Indigo or Etihad)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # --- STRATEGY: TRY AI FIRST ---
        ai_success = False
        if ai_available and not df.empty:
            try:
                # We only give the AI the first 100 rows to prevent it from "freezing"
                context = df.head(100).to_string(index=False)
                prompt = f"Data: {context}\n\nUser: {user_input}\n\nInstruction: If the deal is in the data, explain it. If not, ask for the airline name."
                
                response = model.generate_content(prompt)
                reply = response.text
                response_placeholder.write(reply)
                ai_success = True
            except:
                ai_success = False

        # --- STRATEGY: IF AI FAILS, SHOW DATA IMMEDIATELY ---
        if not ai_success:
            query = user_input.lower()
            # Simple keyword search in the dataframe
            mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
            filtered_df = df[mask]
            
            if not filtered_df.empty:
                response_placeholder.write("I found these matching deals in the sheet:")
                st.dataframe(filtered_df)
                reply = "Displayed matching rows from the sheet."
            else:
                reply = "I couldn't find a deal for that. Please try another airline or check your spelling."
                response_placeholder.write(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
