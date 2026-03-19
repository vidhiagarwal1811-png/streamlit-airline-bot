import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETTINGS & AI ---
st.set_page_config(page_title="Proactive Deal Bot", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Please add your API Key to Secrets.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. DATA LOAD ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data()

# --- 3. THE "PROACTIVE" BRAIN ---
def get_proactive_reply(user_input, dataframe, history):
    # Prepare the data context
    data_str = dataframe.head(100).to_string()
    
    # Format History
    chat_hist = ""
    for m in history[-5:]:
        chat_hist += f"{m['role']}: {m['content']}\n"

    prompt = f"""
    You are a smart, proactive Airline Sales Assistant.
    
    YOUR GOAL: Help the user find the best deal from the sheet. 
    
    STRATEGY:
    1. READ INTENT: Is the user looking for a specific airline? A specific cabin? Or just browsing?
    2. BE PROACTIVE: If the user is vague (e.g., "Show me deals"), ask them which airline or destination they prefer.
    3. USE MEMORY: If they previously mentioned an airline, and now say "any business class?", assume they mean that same airline.
    4. DATA-DRIVEN: Only provide facts found in this sheet:
    {data_str}
    
    CONVERSATION HISTORY:
    {chat_hist}
    
    USER JUST SAID: {user_input}
    
    RESPONSE RULES:
    - If the answer is in the sheet, give it and ask a follow-up (e.g., "Would you like to see the exclusions for this deal?").
    - If information is missing (like cabin class), ASK the user for it.
    - If the airline is not in the sheet, suggest the closest match or ask them to try another one.
    - KEEP IT LIVELY. No boring "No deal found" messages.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "I'm having a little trouble connecting to my brain. Can you try asking about a specific airline?"

# --- 4. THE UI ---
st.title("✈️ Your Proactive Travel Partner")

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if user_input := st.chat_input("Type 'Hi' or ask for a deal..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Checking deals..."):
            ai_response = get_proactive_reply(user_input, df, st.session_state.messages)
            st.markdown(ai_response)
            
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
