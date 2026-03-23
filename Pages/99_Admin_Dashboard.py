import streamlit as st
import os
import sqlite3
import pandas as pd
from agpo_data.research_store import DB_PATH, init_db

st.set_page_config(page_title="Auracelle Charlie 3 - Admin Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>div.block-container{padding-top:0.6rem;}</style>", unsafe_allow_html=True)

init_db()

st.title("🛠️ Administrative Dashboard")

with st.sidebar:
    st.subheader("Access Control")
    pin = st.text_input("Admin PIN", type="password")
    try:
        ADMIN_PIN = st.secrets.get("ADMIN_PIN", None)
    except Exception:
        ADMIN_PIN = None
    if not ADMIN_PIN:
        ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
    authed = (pin == ADMIN_PIN)

if not authed:
    st.info("Enter the Admin PIN in the sidebar to view research stats.")
    st.stop()

con = sqlite3.connect(DB_PATH, check_same_thread=False)
participants = pd.read_sql_query("SELECT * FROM participants", con)
sessions = pd.read_sql_query("SELECT * FROM sessions", con)
moves = pd.read_sql_query("SELECT * FROM moves", con)
outcomes = pd.read_sql_query("SELECT * FROM outcomes", con)
con.close()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Participants", len(participants))
c2.metric("Sessions", len(sessions))
c3.metric("Moves logged", len(moves))
c4.metric("Outcomes recorded", len(outcomes))

st.divider()
st.subheader("Composition Overview (RQ3)")
colA,colB,colC = st.columns(3)
with colA:
    st.write("Gender")
    st.dataframe(participants["gender"].value_counts(dropna=False).rename_axis("gender").reset_index(name="count"))
with colB:
    st.write("Sector")
    st.dataframe(participants["sector"].value_counts(dropna=False).rename_axis("sector").reset_index(name="count"))
with colC:
    st.write("Military status")
    st.dataframe(participants["military_status"].value_counts(dropna=False).rename_axis("military_status").reset_index(name="count"))

st.divider()
st.subheader("Governance Indicators (RQ4)")
if len(outcomes)==0:
    st.warning("No outcomes recorded yet. Ensure the simulation writes outcomes to the outcomes table.")
else:
    st.dataframe(outcomes.sort_values("t", ascending=False))

st.divider()
st.subheader("Export Data")
st.download_button("Download participants.csv", participants.to_csv(index=False), file_name="participants.csv")
st.download_button("Download sessions.csv", sessions.to_csv(index=False), file_name="sessions.csv")
st.download_button("Download moves.csv", moves.to_csv(index=False), file_name="moves.csv")
st.download_button("Download outcomes.csv", outcomes.to_csv(index=False), file_name="outcomes.csv")
