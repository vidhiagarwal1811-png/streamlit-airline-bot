import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETUP ---
st.set_page_config(page_title="Airline Deal Assistant", layout="centered")

# --- 2. AI CONFIGURATION ---
# This looks for the key you saved in Streamlit Secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("🚨 SECRET MISSING: Go to Streamlit Cloud Settings > Secrets and add: GEMINI_API_KEY='your_key_here'")
    st.stop()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"🚨 AI BRAIN ERROR: {e}")
    st.stop()

# --- 3. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_sheet():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"🚨 SHEET ERROR: Could not read Google Sheet. {e}")
        return None

df = load_sheet()

# --- 4. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. USER INTERFACE ---
st.title("✈️ Smart Deal Assistant")
st.write("Ask me about airline deals. I remember our conversation!")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. CHAT LOGIC ---
if user_input := st.chat_input("Ask for a deal..."):
    # Save User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        if df is not None:
            # Prepare context for AI (Sheet data + last few messages for memory)
            data_context = df.head(100).to_string(index=False)
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])

            prompt = f"""
            You are a professional B2B Airline Deal Assistant.
            DATA:
            {data_context}

            MEMORY (Previous Chat):
            {history_context}

            USER INQUIRY: {user_input}

            STRICT RULES:
            1. If the user asks for a cabin (like 'Business') but doesn't name an airline, check the MEMORY to see which airline was discussed last.
            2. Answer using ONLY the data provided. 
            3. Be proactive: if a deal is found, ask if they want to know the validity or exclusions.
            4. If no deal is found, ask for the airline name or IATA code.
            """

            try:
                response = model.generate_content(prompt)
                full_reply = response.text
                st.write(full_reply)
                st.session_state.messages.append({"role": "assistant", "content": full_reply})
            except Exception as e:
                st.error(f"🚨 AI RESPONSE ERROR: {e}")
