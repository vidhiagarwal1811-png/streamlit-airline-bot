# --- CHEAPEST DEAL LOGIC ---
if "cheapest" in query or "best" in query:

    cabin_map = {
        "eco": "eco",
        "economy": "eco",
        "prem": "prem.eco",
        "premium": "prem.eco",
        "bus": "bus",
        "business": "bus",
        "first": "first"
    }

    cabin_column = None

    for key in cabin_map:
        if key in query:
            cabin_column = cabin_map[key]
            break

    if cabin_column and cabin_column in df.columns:

        best_deals = df.sort_values(by=cabin_column).head(5)

        st.write(f"Top deals for {cabin_column}:")
        st.dataframe(best_deals[["airlines", cabin_column]])

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Showing best {cabin_column} deals."
        })

        st.stop()
