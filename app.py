import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Airline Deal Assistant", layout="wide", page_icon="✈️")

# --- 2. DATA LOADING ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Error connecting to data: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. HELPER FUNCTIONS ---
def parse_date_from_text(text):
    """Extracts Month and Year from text to create a comparable date object."""
    if not text or pd.isna(text):
        return None
    text = str(text).lower()
    
    # Look for Month and Year (e.g., March 2026, 31-Mar-26, etc.)
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    month_match = None
    for m in months:
        if m in text:
            month_match = m
            break
            
    year_match = re.search(r'20\d{2}', text)
    if not year_match: # Support for '26 style
        short_year = re.search(r"['\s-](\d{2})(\s|$)", text)
        if short_year:
            year_str = "20" + short_year.group(1)
        else:
            year_str = "2026" # Default
    else:
        year_str = year_match.group()

    if month_match and year_str:
        return datetime.strptime(f"{month_match} {year_str}", "%b %Y")
    elif year_str:
        return datetime.strptime(year_str, "%Y")
    return None

# --- 4. SESSION MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_airline" not in st.session_state:
    st.session_state.current_airline = None

# --- 5. USER INTERFACE ---
st.title("✈️ Airline Deal Assistant")
st.markdown("Search for deals by **Airline Name**, **IATA (EY, AI)**, or **Travel Date**.")

# Display persistent chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(pd.DataFrame([msg["data"]]), use_container_width=True)

# --- 6. CHAT LOGIC ---
if user_input := st.chat_input("Ex: 'Etihad business May 2027'"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    query = user_input.lower().strip()
    
    # A. Search for Airline
    found_row = None
    for _, row in df.iterrows():
        name = str(row.get('airlines name', '')).lower()
        iata = str(row.get('airlines', '')).lower()
        if iata in query or name in query:
            st.session_state.current_airline = row
            found_row = row
            break
    
    # B. Identify Cabin
    cabin = None
    if any(x in query for x in ["bus", "business"]): cabin = "bus"
    elif any(x in query for x in ["eco", "economy"]): cabin = "eco"
    elif any(x in query for x in ["prem", "premium"]): cabin = "prem. eco"
    elif "first" in query: cabin = "first"

    # C. Date Validation
    requested_date = parse_date_from_text(query)

    # D. Build Response
    with st.chat_message("assistant"):
        # Use found row or fall back to memory
        active_row = found_row if found_row is not None else st.session_state.current_airline
        
        if active_row is not None:
            airline_name = str(active_row.get('airlines name', 'UNKNOWN')).upper()
            validity_str = str(active_row.get('validity', 'No data'))
            validity_date = parse_date_from_text(validity_str)

            # Check Date Validity
            if requested_date and validity_date and requested_date > validity_date:
                response = f"❌ **No Available Deal.** The deals for **{airline_name}** are valid only until **{validity_str}**. Your requested travel date is beyond this period."
                display_data = None
            else:
                if cabin:
                    price = active_row.get(cabin, "N/A")
                    response = f"✅ **{airline_name}** {cabin.upper()} deal found: **{price}**.\n\n*Validity: {validity_str}*"
                else:
                    response = f"I found the deals for **{airline_name}** (Valid until {validity_str}). Which cabin (Eco, Business, First) would you like to check?"
                display_data = active_row
            
            # Show output
            st.write(response)
            if display_data is not None:
                st.dataframe(pd.DataFrame([display_data]), use_container_width=True)
            
            # Save to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "data": display_data
            })
        else:
            response = "I couldn't find that airline. Please specify the Airline name or IATA code (e.g., EY, AI)."
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response, "data": None})
