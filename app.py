import streamlit as st
import pandas as pd
import calendar
import google.generativeai as genai

# --- 1. CONFIG ---
st.set_page_config(page_title="Deal Sheet Bot", layout="wide")

# --- 2. AI SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("API Key not found in Secrets!")

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. DATA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame()

df = load_data(SHEET_URL)

# --- 5. NLP WITH MEMORY ---
def get_ai_reply(user_query, dataframe, history):
    # Only send 50 rows to keep it fast and avoid errors
    data_summary = dataframe.head(50).to_string()
    
    chat_history = ""
    for m in history[-3:]: # Only last 3 messages for speed
        chat_history += f"{m['role']}: {m['content']}\n"

    prompt = f"""
    Use this Airline Deal Data:
    {data_summary}

    Context: {chat_history}
    User Question: {user_query}

    Instructions:
    1. Answer concisely based ONLY on the data.
    2. If unsure or missing, say 'FALLBACK'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "FALLBACK"

# --- 6. UI ---
st.title("✈️ Airline Deal Assistant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Ask about a deal..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            ai_reply = get_ai_reply(user_input, df, st.session_state.messages)
            
            if ai_reply != "FALLBACK":
                st.write(ai_reply)
                final_reply = ai_reply
            else:
                # --- HARDCODED FALLBACK LOGIC ---
                query = user_input.lower()
                words = query.split()
                
                # Simple Airline match
                match = df[df.apply(lambda row: any(str(val).lower() in query for val in row), axis=1)]
                
                if not match.empty:
                    st.write("I found these relevant deals in the sheet:")
                    st.dataframe(match)
                    final_reply = "Displaying matching deals from the sheet."
                else:
                    final_reply = "I couldn't find that deal. Please check the airline name or IATA code."
                    st.write(final_reply)

    st.session_state.messages.append({"role": "assistant", "content": final_reply})
