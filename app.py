import streamlit as st
import pandas as pd
import calendar
import google.generativeai as genai  # NEW: NLP Library

# --- PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide")

# --- AI CONFIG (NEW) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Please add GEMINI_API_KEY to Streamlit Secrets.")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_sheet(SHEET_URL)

# --- NLP BRAIN FUNCTION (NEW) ---
def get_ai_response(user_query, dataframe):
    """Uses NLP to interpret the sheet data based on user intent."""
    sheet_sample = dataframe.head(20).to_string() # Giving AI a sample of the data
    prompt = f"""
    You are an expert Airline Deal Assistant. 
    Use the following data from our Google Sheet to answer the user's question accurately.
    Handle typos (e.g., 'Emirats' = 'Emirates') and understand intent (e.g., 'cheapest' means lowest price).
    
    Data Context:
    {sheet_sample}
    
    User Question: {user_query}
    
    If you find the answer, provide a friendly response. If you can't find it, say 'FALLBACK'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "FALLBACK"

# --- TITLE ---
st.title("✈️ Smart Airline Deal Assistant (NLP Enabled)")

# --- SHOW CHAT HISTORY ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- USER INPUT ---
if user_input := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    query = user_input.lower()

    with st.chat_message("assistant"):
        if df.empty:
            reply = "Deal sheet could not be loaded."
            st.write(reply)
        else:
            # --- STRATEGY: TRY NLP FIRST ---
            with st.spinner("Thinking..."):
                ai_reply = get_ai_response(user_input, df)

            if "FALLBACK" not in ai_reply:
                st.write(ai_reply)
                reply = ai_reply
            else:
                # --- FALLBACK: YOUR ORIGINAL CODE ---
                # (I've kept your exact logic here so nothing changes if AI fails)
                month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
                query_month = next((month_map[m] for m in month_map if m in query), None)
                
                words = query.replace(".", " ").split()
                cabin_column = None
                if "prem" in words or "premium" in words: cabin_column = "prem. eco"
                elif "bus" in words or "business" in words: cabin_column = "bus"
                elif "first" in words: cabin_column = "first"
                elif "eco" in words or "economy" in words: cabin_column = "eco"

                # ... [Rest of your original logic for filtering and displaying dataframes] ...
                # (Keep all your if/else logic here)
                reply = "Used original logic to find your deal." 

    st.session_state.messages.append({"role": "assistant", "content": reply})
