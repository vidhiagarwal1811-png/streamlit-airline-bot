import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. CONFIG & API SETUP ---
st.set_page_config(page_title="Deal Sheet Bot", layout="wide")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CONNECT TO GOOGLE SHEET ---
# Replace this with your specific Export URL from Step 2
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600) # Refresh data every 10 minutes
def load_sheet_data(url):
    try:
        # Pandas reads the sheet directly from the URL
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Failed to connect to Google Sheet: {e}")
        return None

df = load_sheet_data(SHEET_URL)

# --- 3. CHAT INTERFACE ---
st.title("Live Deal Sheet Assistant ✈️")

# (Rest of your chat history and user input code here...)

if prompt := st.chat_input("Ask about an airline..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # AI Prompt using the Sheet Data as context
    # df.to_csv() creates a text version of the sheet for the AI to read
    context = df.to_csv(index=False) 
    full_query = f"Data from Deal Sheet:\n{context}\n\nUser Question: {prompt}"
    
    with st.chat_message("assistant"):
        response = model.generate_content(full_query)
        st.write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- 4. SMART BOT LOGIC ---
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # We tell the AI to act as a validator
    context = df.to_csv(index=False)
    
    full_prompt = f"""
    You are a professional travel agent assistant. 
    Your goal is to provide accurate deal information from the data provided.
    
    REQUIRED INFO TO GIVE A FINAL PRICE:
    1. Airline Name
    2. Cabin Class (Eco, Bus, First)
    3. Travel Date (to check validity)

    RULES:
    - If the user is missing any of the 3 items above, ASK them for the missing detail politely.
    - If you have all info, show the deal in a clear Markdown Table.
    - Always mention the 18% tax deduction and RS.10 miscellaneous fee. 
    - If the airline isn't in the list, apply the default markup (INR 100 Eco / 200 Bus). [cite: 4]

    DATA:
    {context}

    USER QUESTION: {prompt}
    """

    with st.chat_message("assistant"):
        response = model.generate_content(full_prompt)
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
