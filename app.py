import streamlit as st
import pandas as pd

CSV_URL = "https://docs.google.com/spreadsheets/d/1kwHFOIpTZ3qhk3JoiXxP68-tJGnfrPxkLoyRObQ4314/export?format=csv"

@st.cache_data
def load_data():
    return pd.read_csv(CSV_URL)

data = load_data()

st.title("Airline Deals Bot")

query = st.text_input("Ask your question:")

if query:
    query = query.lower()
    found = False
    for i, row in data.iterrows():
        airline_name = str(row.get("Airlines Name", "")).lower()
        airline_code = str(row.get("Airlines", "")).lower()
        if airline_name in query or airline_code in query:
            st.write(f"**Airline:** {row['Airlines Name']}")
            st.write(f"**First Class:** {row['First']}")
            st.write(f"**Business Class:** {row['Bus']}")
            st.write(f"**Premium Economy:** {row['Prem eco']}")
            st.write(f"**Economy:** {row['Eco']}")
            st.write(f"**Validity:** {row['Validity']}")
            st.write(f"**Note:** {row['Note']}")
            found = True
            break
    if not found:
        st.write("Sorry, no info found.")
