import streamlit as st
import pandas as pd
import re

# --- 1. SETUP & DATA ---
st.set_page_config(page_title="Strict Deal Bot", layout="wide")

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

# --- 2. THE DATE SCORER (THE BRAINS) ---
def get_date_score(text):
    """Converts 'Dec 2026' or '31 MAR 26' into a number like 202612."""
    if not text or pd.isna(text): return None
    text = str(text).lower()
    
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    
    # 1. Find Month
    m_val = next((v for k, v in months.items() if k in text), 0)
    
    # 2. Find Year (Handles 2026, 26, or '26)
    y_match = re.findall(r'\b20\d{2}\b|\b\d{2}\b', text)
    if not y_match or m_val == 0: return None
    
    # We take the last number found as the year
    y_str = y_match[-1]
    y_val = int(y_str) if len(y_str) == 4 else int("20" + y_str)
    
    return (y_val * 100) + m_val

# --- 3. UI & LOGIC ---
st.title("✈️ Strict Airline Deal Assistant")

if user_input := st.chat_input("Ex: 'EY eco dec 2026'"):
    query = user_input.lower().strip()
    user_score = get_date_score(query)

    # Find Airline
    target_row = None
    for _, row in df.iterrows():
        iata = str(row.get('airlines', '')).lower()
        name = str(row.get('airlines name', '')).lower()
        if iata in query or (len(name) > 3 and name in query):
            target_row = row
            break

    if target_row is not None:
        val_text = str(target_row.get('validity', ''))
        sheet_score = get_date_score(val_text)
        airline_name = str(target_row.get('airlines name', '')).upper()

        # --- THE BLOCKADE ---
        if user_score and sheet_score and user_score > sheet_score:
            st.error(f"❌ **No Available Deal.**")
            st.write(f"The deals for **{airline_name}** are only valid until **{val_text}**.")
            # NO DATAFRAME IS SHOWN HERE.
        else:
            # Only identify cabin if date is valid
            cabin = next((c for c in ["bus", "eco", "first"] if c in query or (c=="bus" and "business" in query)), "eco")
            price = target_row.get(cabin, "N/A")
            
            st.success(f"✅ Deal Found! **{airline_name}** {cabin.upper()} is **{price}**.")
            st.write(f"*Validity: {val_text}*")
            st.dataframe(pd.DataFrame([target_row]), use_container_width=True)
    else:
        st.info("Airline not found. Try 'EY' or 'Air India'.")
