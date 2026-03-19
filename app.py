import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETUP & THEMES ---
st.set_page_config(page_title="Proactive Deal Assistant", layout="centered", page_icon="✈️")

# --- 2. CONNECT TO THE BRAIN (GEMINI) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Brain connection failed: {e}")
else:
    st.error("Missing GEMINI_API_KEY in Streamlit Secrets!")

# --- 3. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. LOAD THE DATA (THE GOOGLE SHEET) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60) # Refreshes every minute
def load_live_deals():
    try:
        # We read the sheet and force everything to string to avoid math errors
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Could not read Google Sheet: {e}")
        return pd.DataFrame()

df = load_live_deals()

# --- 5. THE BRAIN FUNCTION (REBUILT) ---
def get_ai_response(user_input, dataframe, history):
    # Convert the actual sheet data into a clean text block for the AI
    # This ensures the AI is actually "Reading" the sheet
    sheet_as_text = dataframe.to_string(index=False)
    
    # Create the conversation thread
    chat_context = ""
    for m in history[-5:]:
        chat_context += f"{m['role']}: {m['content']}\n"

    # THE MASTER PROMPT
    prompt = f"""
    SYSTEM: You are a professional B2B Travel Sales Assistant. 
    You have DIRECT ACCESS to the following live Deal Sheet data.
    
    LIVE DATA FROM GOOGLE SHEET:
    {sheet_as_text}
    
    CONVERSATION HISTORY:
    {chat_context}
    
    USER INQUIRY: {user_input}
    
    STRICT RULES:
    1. READ INTENT: If the user says 'Hi' or is vague, ask them what airline or cabin they are looking for.
    2. MEMORY: If they previously asked about 'Air India' and now say 'what about business?', you MUST answer for Air India Business class.
    3. PRECISION: Only give deals that exist in the table above. If an airline isn't there, say you don't have that specific deal but suggest an alternative from the list.
    4. PROACTIVE: Always end with a helpful question like "Would you like to know the validity for this?" or "Should I check another airline?"
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I'm having trouble thinking right now. Error: {str(e)}"

# --- 6. CHAT INTERFACE ---
st.title("✈️ Smart Airline Deal Assistant")
st.write("Ask me about airline deals, cabin classes, or validity!")

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Chat Input
if user_input := st.chat_input("Ask me anything..."):
    # Save & Show User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate & Show Assistant Message
    with st.chat_message("assistant"):
        with st.spinner("Consulting the Deal Sheet..."):
            full_response = get_ai_response(user_input, df, st.session_state.messages)
            st.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
