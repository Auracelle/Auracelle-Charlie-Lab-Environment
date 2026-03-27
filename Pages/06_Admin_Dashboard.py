"""
pages/06_Admin_Dashboard.py — Research data admin panel.

Gated by: authentication + admin PIN (env var ADMIN_PIN or st.secrets["ADMIN_PIN"]).
Reads: sessions, participants, moves, outcomes from SQLite.
"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from storage.research_store import (
    init_db,
    fetch_all_sessions,
    fetch_all_participants,
)
from storage.session_state import init_session_defaults, require_auth

st.set_page_config(
    page_title="Auracelle Charlie — Admin Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("<style>div.block-container{padding-top:0.6rem;}</style>", unsafe_allow_html=True)

init_session_defaults()
require_auth()
init_db()

st.title("🛠️ Administrative Dashboard")

# ── Admin PIN gate ────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Access Control")
    pin = st.text_input("Admin PIN", type="password")

    # Read PIN from secrets or env; never hardcode for real deployments
    try:
        ADMIN_PIN = st.secrets.get("ADMIN_PIN", None)
    except Exception:
        ADMIN_PIN = None
    if not ADMIN_PIN:
        ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")

    authed = (pin == ADMIN_PIN)

if not authed:
    st.info("Enter the Admin PIN in the sidebar to view research statistics.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
import sqlite3
from config.constants import DB_PATH
from pathlib import Path

if not Path(DB_PATH).exists():
    st.warning("Research database not found. Run a simulation session first.")
    st.stop()

con = sqlite3.connect(DB_PATH, check_same_thread=False)

try:
    participants = pd.read_sql_query("SELECT * FROM participants", con)
    sessions     = pd.read_sql_query("SELECT * FROM sessions",     con)
    moves        = pd.read_sql_query("SELECT * FROM moves",        con)
    outcomes     = pd.read_sql_query("SELECT * FROM outcomes",     con)
finally:
    con.close()

# ── Summary metrics ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Participants",        len(participants))
c2.metric("Sessions",            len(sessions))
c3.metric("Moves logged",        len(moves))
c4.metric("Outcomes recorded",   len(outcomes))

st.divider()

# ── Participant composition (RQ3) ─────────────────────────────────────────────
st.subheader("Composition Overview (RQ3)")
colA, colB, colC = st.columns(3)

with colA:
    st.write("Gender")
    if not participants.empty and "gender" in participants.columns:
        df_g = participants["gender"].value_counts(dropna=False).rename_axis("gender").reset_index(name="count")
        st.dataframe(df_g, use_container_width=True)
        fig = px.pie(df_g, names="gender", values="count", title="Gender distribution")
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=35, b=0))
        st.plotly_chart(fig, use_container_width=True)

with colB:
    st.write("Sector")
    if not participants.empty and "sector" in participants.columns:
        df_s = participants["sector"].value_counts(dropna=False).rename_axis("sector").reset_index(name="count")
        st.dataframe(df_s, use_container_width=True)
        fig = px.pie(df_s, names="sector", values="count", title="Sector distribution")
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=35, b=0))
        st.plotly_chart(fig, use_container_width=True)

with colC:
    st.write("Military status")
    if not participants.empty and "military_status" in participants.columns:
        df_m = participants["military_status"].value_counts(dropna=False).rename_axis("military_status").reset_index(name="count")
        st.dataframe(df_m, use_container_width=True)

st.divider()

# ── Extended composition ──────────────────────────────────────────────────────
st.subheader("Extended Profile Breakdown")
colD, colE, colF = st.columns(3)

for col, field, label in [
    (colD, "ai_gov_familiarity",  "AI Governance Familiarity"),
    (colE, "wargame_experience",  "Wargaming Experience"),
    (colF, "role_function",       "Role Function"),
]:
    with col:
        st.write(label)
        if not participants.empty and field in participants.columns:
            df_f = participants[field].value_counts(dropna=False).rename_axis(field).reset_index(name="count")
            st.dataframe(df_f, use_container_width=True)

st.divider()

# ── Governance indicators (RQ4) ───────────────────────────────────────────────
st.subheader("Governance Indicators (RQ4)")
if outcomes.empty:
    st.warning("No outcomes recorded yet. Ensure the simulation writes outcomes to the outcomes table.")
else:
    st.dataframe(outcomes.sort_values("t", ascending=False), use_container_width=True)
    numeric_cols = [c for c in ["trust", "compliance", "alignment", "resilience"] if c in outcomes.columns]
    if numeric_cols:
        fig = px.box(
            outcomes[numeric_cols],
            title="Outcome distribution across sessions",
            labels={"variable": "Metric", "value": "Score (0–1)"},
        )
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Raw data explorer ─────────────────────────────────────────────────────────
with st.expander("🔍 Raw Data Explorer", expanded=False):
    table = st.selectbox("Table", ["participants", "sessions", "moves", "outcomes"])
    if table == "participants":
        st.dataframe(participants, use_container_width=True)
    elif table == "sessions":
        st.dataframe(sessions, use_container_width=True)
    elif table == "moves":
        st.dataframe(moves, use_container_width=True)
    elif table == "outcomes":
        st.dataframe(outcomes, use_container_width=True)

# ── CSV export ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📥 Export Research Data")

col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
with col_exp1:
    if not participants.empty:
        st.download_button("Download Participants CSV", participants.to_csv(index=False),
                           file_name="charlie_participants.csv", mime="text/csv", use_container_width=True)
with col_exp2:
    if not sessions.empty:
        st.download_button("Download Sessions CSV", sessions.to_csv(index=False),
                           file_name="charlie_sessions.csv", mime="text/csv", use_container_width=True)
with col_exp3:
    if not moves.empty:
        st.download_button("Download Moves CSV", moves.to_csv(index=False),
                           file_name="charlie_moves.csv", mime="text/csv", use_container_width=True)
with col_exp4:
    if not outcomes.empty:
        st.download_button("Download Outcomes CSV", outcomes.to_csv(index=False),
                           file_name="charlie_outcomes.csv", mime="text/csv", use_container_width=True)
