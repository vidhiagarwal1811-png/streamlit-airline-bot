import streamlit as st
import pandas as pd
import calendar
import google.generativeai as genai

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide", page_icon="✈️")

# --- 2. AI CONFIGURATION (NLP) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # We use gemini-1.5-flash for speed and efficiency
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Missing API Key! Please add GEMINI_API_KEY to Streamlit Secrets.")

# --- 3. SESSION STATE (MEMORY) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        # Standardize column names for easier searching
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
        return pd.DataFrame()

df = load_sheet(SHEET_URL)

# --- 5. NLP BRAIN WITH CONTEXTUAL MEMORY ---
def get_nlp_response(user_query, dataframe, chat_history):
    """
    Sends the sheet data and previous chat context to the AI.
    """
    # Convert dataframe to string for the AI to read (first 100 rows)
    data_context = dataframe.head(100).to_string()
    
    # Format the last 5 messages as context so the AI remembers the conversation
    history_context = ""
    for msg in chat_history[-5:]:
        history_context += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""
    ROLE: You are an expert Travel Advisor for an internal Airline Deal Sheet.
    
    MEMORY (Previous conversation):
    {history_context}
    
    DATA (Current Deal Sheet):
    {data_context}
    
    USER QUESTION: {user_query}
    
    INSTRUCTIONS:
    1. Answer using ONLY the provided Data. 
    2. If the user refers to 'it', 'this airline', or a cabin class (e.g., 'What about Business?') without naming the airline, check the MEMORY to see which airline was last discussed.
    3. Be professional and concise. 
    4. If the data is missing or the question is unrelated to airline deals, reply ONLY with: FALLBACK.
    5. Do NOT mention the word 'Fallback' in your final user-facing response.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "FALLBACK"

# --- 6. UI HEADER ---
st.title("✈️ Smart Airline Deal Assistant")
st.caption("AI-Powered | Memory Enabled | Grounded in Deal Sheet")

# Sidebar to clear chat/memory
if st.sidebar.button("Clear Chat Memory"):
    st.session_state.messages = []
    st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 7. MAIN INTERACTION ---
if user_input := st.chat_input("Ex: 'Air India deals' then 'What about Business class?'"):
    
    # Save User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower()

    with st.chat_message("assistant"):
        if df.empty:
            reply = "I'm sorry, I can't access the deal sheet right now."
            st.write(reply)
        else:
            with st.spinner("Searching..."):
                # Pass current query, the dataframe, and the history for memory
                ai_reply = get_nlp_response(user_input, df, st.session_state.messages)

            if ai_reply != "FALLBACK" and len(ai_reply) > 2:
                # Successful NLP retrieval
                st.write(ai_reply)
                reply = ai_reply
            else:
                # --- STEP 8: ORIGINAL LOGIC FALLBACK (NO 'FALLBACK' TEXT) ---
                month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
                query_month = next((month_map[m] for m in month_map if m in query), None)
                
                words = query.replace(".", " ").split()
                
                #
