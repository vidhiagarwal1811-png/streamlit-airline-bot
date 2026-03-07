import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. CONFIG & API SETUP ---
st.set_page_config(page_title="Deal Sheet Bot", layout="wide")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])  # Add your API key in Streamlit secrets
MODEL_NAME = "gemini-1.5-flash"

# --- 2. INITIALIZE CHAT STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. CONNECT TO GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Failed to load Google Sheet: {e}")
        return pd.DataFrame()

df = load_sheet(SHEET_URL)

# --- 4. APP UI ---
st.title("Live Deal Sheet Assistant ✈️")

# Show previous chat messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# User input
if user_input := st.chat_input("Ask about an airline..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Prepare context for AI
    sheet_context = df.to_csv(index=False)
    full_prompt = f"""
You are a professional travel agent assistant. Your goal is to provide accurate deal information from the provided data.

REQUIRED INFO TO GIVE FINAL PRICE:
1. Airline Name
2. Cabin Class (Eco, Bus, First)
3. Travel Date

RULES:
- If user misses any of the above, ask politely for missing details.
- If all info is present, show the deal in a Markdown Table.
- Always mention the 18% tax deduction and Rs.10 miscellaneous fee.
- If airline not in sheet, apply default markup (INR 100 Eco / 200 Bus).

DATA:
{sheet_context}

USER QUESTION: {user_input}
"""

    with st.chat_message("assistant"):
        # Correct method to generate AI response
        response = genai.generate_text(model=MODEL_NAME, prompt=full_prompt)
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
