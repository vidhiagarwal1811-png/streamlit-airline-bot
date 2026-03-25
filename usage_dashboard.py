import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Usage Dashboard", layout="wide")

LOG_FILE = "usage_log.csv"

st.title("📊 App Usage Dashboard")

if os.path.exists(LOG_FILE):
    df = pd.read_csv(LOG_FILE, parse_dates=["timestamp"])

    df['date'] = df['timestamp'].dt.date

    total_visits = len(df)
    unique_users = df['user_id'].nunique()
    avg_usage = round(total_visits / unique_users, 2)

    daily_visits = df.groupby('date').size()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Visits", total_visits)
    col2.metric("Unique Users", unique_users)
    col3.metric("Avg Visits/User", avg_usage)

    st.divider()
    st.subheader("📈 Daily Usage Trend")
    st.line_chart(daily_visits)

    with st.expander("🔍 Raw Data"):
        st.dataframe(df)

else:
    st.warning("No usage data found. Make sure tracking is enabled in main app.")
