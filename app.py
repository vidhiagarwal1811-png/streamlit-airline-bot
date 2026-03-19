import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. CONFIG ---
st.set_page_config(page_title="Deal Bot", layout="centered")

# --- 2. AI CONNECTION ---
# We use 'try' so that even if the AI fails, the App STILL LOADS
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Missing GEMINI_API_KEY in Secrets!")
    st.stop()

try:
    genai.configure(api_key=api_key)
    # Using 'gemini-pro' as it is the most stable name across all versions
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.warning(f"AI Brain offline. Error: {e}")

# --- 3. DATA LOAD ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        data.columns = data.columns.str.strip().str.lower()
        return data
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. CHAT INTERFACE ---
st.title("✈️ Smart Deal Bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Ask for a deal..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        # Memory Logic: Check last 3 messages
        history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-3:]])
        
        # Data Logic: Send first 50 rows only to keep it fast
        context = df.head(50).to_string(index=False)
        
        prompt = f"Data: {context}\n\nHistory: {history}\n\nUser: {user_input}\n\nAnswer based ONLY on data. If vague, ask for the airline."
        
        try:
            response = model.generate_content(prompt)
            st.write(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI failed to respond. Technical Error: {e}")
