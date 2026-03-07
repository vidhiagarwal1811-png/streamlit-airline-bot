import streamlit as st
import pandas as pd

st.title("✈️ Airline Deal Bot")

# Upload Excel
uploaded_file = st.file_uploader("Upload Deal Sheet", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Clean dataframe
    df.columns = df.columns.str.strip().str.lower()
    df = df.fillna("")

    query = st.text_input("Ask deal (example: EY business / cheapest eco deal)").lower()

    if query:

        words = query.split()

        cabin = None
        airline_found = None
        result = None

        # Detect cabin class
        if "eco" in query:
            cabin = "eco"

        elif "prem" in query or "premium" in query:
            cabin = "prem. eco"

        elif "bus" in query or "business" in query:
            cabin = "bus"

        elif "first" in query:
            cabin = "first"

        else:
            st.warning("Please specify cabin class: Eco / Prem.Eco / Bus / First")

        # Detect airline
        for _, row in df.iterrows():

            airline = str(row["airlines"]).lower()
            airline_name = str(row["airlines name"]).lower()
            iata = str(row["iata"]).lower()

            # Exact IATA match
            if iata in words:
                airline_found = airline
                result = df[df["iata"].str.lower() == iata]
                break

            # Airline code match
            if airline in words:
                airline_found = airline
                result = df[df["airlines"].str.lower() == airline]
                break

            # Airline name match
            if airline_name in query:
                airline_found = airline
                result = df[df["airlines name"].str.lower() == airline_name]
                break

        # If airline found
        if result is not None and cabin:

            row = result.iloc[0]

            st.write(f"✈️ **{row['airlines name']} ({row['airlines']})**")

            deal = row[cabin]

            if deal:
                st.write(f"📌 **{cabin.upper()} Deal:** {deal}")
            else:
                st.write("❌ No deal available")

            if row["validity"]:
                st.write(f"📅 **Validity:** {row['validity']}")

            if row["exclusions"]:
                st.write(f"⚠️ **Exclusions:** {row['exclusions']}")

            if row["note"]:
                st.write(f"📝 **Note:** {row['note']}")

            st.subheader("📊 Full Deal Row")
            st.dataframe(result)

        else:
            st.error("Airline or deal not found")
