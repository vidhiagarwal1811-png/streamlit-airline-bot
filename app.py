import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Smart Deal Assistant", layout="centered", page_icon="✈️")

# --- 2. AI CONFIGURATION ---
# We use a try/except block so the app never "dies" even if the API fails
ai_ready = False
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Using the most stable model identifier
        model = genai.GenerativeModel('gemini-1.5-flash')
        ai_ready = True
    except Exception as e:
        st.warning(f"AI Brain is offline, but I can still show you the sheet. (Error: {e})")
else:
    st.error("Please add GEMINI_API_KEY to your Streamlit Secrets!")

# --- 3. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. UI ---
st.title("✈️ Smart Airline Deal Bot")
st.write("I remember our conversation! Ask me about an airline or a cabin.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. CHAT LOGIC ---
if user_input := st.chat_input("Ex: 'Air India deals' then 'What about business class?'"):
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response_text = ""
        
        # --- STRATEGY A: THE AI BRAIN (WITH MEMORY) ---
        if ai_ready and not df.empty:
            try:
                # We give the AI the sheet data AND the last 5 messages for memory
                data_context = df.head(100).to_string(index=False)
                history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                
                prompt = f"""
                You are a proactive Airline Deal Assistant. 
                Use this data: {data_context}
                
                Conversation History: {history_context}
                Current User Question: {user_input}
                
                RULES:
                1. If the user refers to 'it' or asks for a cabin class, use the History to know which airline they mean.
                2. Be conversational. Ask follow-up questions like 'Would you like to see the validity?'
                3. If the airline is not in the data, tell them clearly.
                """
                
                response = model.generate_content(prompt)
                response_text = response.text
                st.markdown(response_text)
                
            except Exception as e:
                # If AI fails (404 error etc), we silently switch to Strategy B
                ai_ready = False 

        # --- STRATEGY B: THE SEARCH BACKUP (If AI Fails) ---
        if not ai_ready or response_text == "":
            query = user_input.lower()
            # Simple keyword match in the dataframe
            match = df[df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]
            
            if not match.empty:
                response_text = "I found these matching deals in the sheet for you:"
                st.write(response_text)
                st.dataframe(match)
            else:
                response_text = "I couldn't find that specific deal. Could you please specify the airline name?"
                st.write(response_text)

    # Save assistant response to memory
    st.session_state.messages.append({"role": "assistant", "content": response_text})
