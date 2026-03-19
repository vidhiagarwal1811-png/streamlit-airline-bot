import streamlit as st
import pandas as pd
import calendar
import google.generativeai as genai

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Deal Sheet Assistant", layout="wide")

# --- 2. AI CONFIGURATION (NLP BRAIN) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Please add GEMINI_API_KEY to Streamlit Secrets to enable NLP features.")

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return pd.DataFrame()

df = load_sheet(SHEET_URL)

# --- 5. NLP BRAIN FUNCTION ---
def get_nlp_response(user_query, dataframe):
    """
    Sends the sheet data and user query to Gemini.
    Strictly instructed to stay within the sheet data.
    """
    # We send a text version of the dataframe to the AI
    # (Limited to first 60 rows to fit within AI 'context window' safely)
    data_context = dataframe.head(60).to_string()

    prompt = f"""
    ROLE: You are an expert Airline Deal Assistant.
    STRICT DATA SOURCE: Use ONLY the provided Google Sheet data below.
    
    INSTRUCTIONS:
    1. If the answer is in the data, provide a friendly, professional response.
    2. Handle typos (e.g., 'Indigo' for 'IndiGo', 'Emirats' for 'Emirates').
    3. Understand intent: 'cheapest' means lowest numeric value in the cabin columns.
    4. CRITICAL: If the user asks for something NOT in the data, or if you are unsure, 
       respond ONLY with the word: FALLBACK.
    5. Do NOT use your own external knowledge or make up prices.
    
    SHEET DATA:
    {data_context}
    
    USER QUESTION: {user_query}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "FALLBACK"

# --- 6. UI LAYOUT ---
st.title("✈️ Smart Airline Deal Assistant")
st.markdown("---")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 7. MAIN LOGIC ---
if user_input := st.chat_input("Ex: What are the cheapest Indigo deals for March?"):
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower()
    reply = ""

    with st.chat_message("assistant"):
        if df.empty:
            reply = "I'm sorry, the deal sheet could not be loaded at this time."
            st.write(reply)
        else:
            with st.spinner("Searching deals..."):
                # --- STEP 1: TRY NLP FIRST ---
                ai_response = get_nlp_response(user_input, df)

            if ai_response != "FALLBACK" and len(ai_response) > 2:
                # Success! AI found it in the sheet.
                st.write(ai_response)
                reply = ai_response
            else:
                # --- STEP 2: ORIGINAL LOGIC FALLBACK ---
                # This part is your original code exactly, acting as a safety net.
                month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
                query_month = next((month_map[m] for m in month_map if m in query), None)
                
                words = query.replace(".", " ").split()
                cabin_column = None
                if "prem" in words or "premium" in words: cabin_column = "prem. eco"
                elif "bus" in words or "business" in words: cabin_column = "bus"
                elif "first" in words: cabin_column = "first"
                elif "eco" in words or "economy" in words: cabin_column = "eco"

                # Original detection logic for Airlines
                filtered_df = df.copy()
                airline_found = None
                for _, row in df.iterrows():
                    airline = str(row.get("airlines", "")).lower()
                    airline_name = str(row.get("airlines name", "")).lower()
                    iata = str(row.get("iata", "")).lower()

                    if iata in words or airline in words or airline_name in query:
                        airline_found = airline
                        filtered_df = df[df["airlines"].str.lower() == airline]
                        break

                # Final display logic
                if not airline_found:
                    reply = "I couldn't find that airline. Please try an IATA code or full name."
                elif not cabin_column:
                    reply = "Which cabin class are you looking for? (Eco, Business, etc.)"
                else:
                    if filtered_df.empty:
                        reply = "No deals found for that selection."
                    else:
                        row = filtered_df.iloc[0]
                        deal_val = row.get(cabin_column, "N/A")
                        reply = f"The {cabin_column.upper()} deal for {row['airlines name']} is {deal_val}."
                        st.write(reply)
                        st.dataframe(filtered_df)

                if not reply: reply = "I'm sorry, I couldn't find a matching deal in the sheet."
                st.write(reply)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": reply})
