import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- SETUP & DATA ---
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

# Helper function to convert text like "March 2026" into a comparable date object
def parse_month_year(text):
    if not text or pd.isna(text):
        return None
    # Try to find Month name and Year
    match = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec).*?(20\d{2})', str(text).lower())
    if match:
        month_str = match.group(1)
        year_str = match.group(2)
        # Convert to a date object (using the 1st of that month)
        return datetime.strptime(f"{month_str} {year_str}", "%b %Y")
    # Fallback to just Year if no month is found
    year_match = re.search(r'20\d{2}', str(text))
    if year_match:
        return datetime.strptime(year_match.group(), "%Y")
    return None

# --- UI & LOGIC ---
if user_input := st.chat_input("Enter airline and travel date"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    query = user_input.lower().strip()
    
    # 1. Parse User's Requested Date
    requested_date = parse_month_year(query)

    # 2. Find Airline
    active_row = None
    for _, row in df.iterrows():
        name = str(row.get('airlines name', '')).lower()
        iata = str(row.get('airlines', '')).lower()
        if iata in query or name in query:
            active_row = row
            break

    with st.chat_message("assistant"):
        if active_row is not None:
            validity_text = str(active_row.get('validity', ''))
            validity_date = parse_month_year(validity_text)

            # --- VALIDATION CHECK ---
            if requested_date and validity_date and requested_date > validity_date:
                reply = f"❌ **No Available Deal.** Your requested travel date is beyond the validity of this deal (**{validity_text}**)."
                st.error(reply)
            else:
                # Show deal as normal
                cabin = "eco" # Default or logic to find cabin
                deal = active_row.get(cabin, "N/A")
                reply = f"✅ Deal Found! **{active_row.get('airlines name')}** {cabin.upper()} is **{deal}**."
                st.success(reply)
                st.table(pd.DataFrame([active_row]))
        else:
            st.write("Airline not found. Try searching for 'EY' or 'Air India'.")
