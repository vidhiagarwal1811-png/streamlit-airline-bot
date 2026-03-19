import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETUP ---
st.set_page_config(page_title="Deal Assistant", layout="centered")

# --- 2. THE BRAIN CHECK ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("🚨 SECRET ERROR: I can't find 'GEMINI_API_KEY' in your App Secrets.")
    st.stop()
else:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # UPDATED: We use 'gemini-1.5-flash-latest' to fix the 404 error
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        st.error(f"🚨 BRAIN ERROR: {e}")
        st.stop()

# --- 3. DATA LOAD ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def get_data():
    try:
        data = pd.read_csv(SHEET_URL)
        data.columns = data.columns.str.strip().str.lower()
        return data
    except Exception as e:
        st.error(f"🚨 SHEET ERROR: I can't read the Google Sheet. Error: {e}")
        return None

df = get_data()

# --- 4. CHAT INTERFACE ---
st.title("✈️ Smart Deal Bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Ask me for a deal..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        if df is not None:
            # We only send the top 100 rows to keep it fast and avoid timeouts
            sheet_text = df.head(100).to_string(index=False)
            
            # Creating a simple history for memory
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-3:]])
            
            prompt = f"""
            You are a helpful Airline Deal Assistant.
            DATA:
            {sheet_text}
            
            CONVERSATION HISTORY:
            {history_context}
            
            USER QUESTION: {user_input}
            
            INSTRUCTIONS:
            - If the user is vague, ask which airline or cabin they need.
            - If they previously mentioned an airline, assume they are still talking about it.
            - Be professional and proactive.
            """
            
            try:
                response = model.generate_content(prompt)
                reply = response.text
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                # If it still fails, we show a helpful error
                st.error(f"🚨 AI ERROR: {e}")
