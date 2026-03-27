"""
pages/05_Real_World_Data_Metrics.py — Real-world indicator panel.

Gated by: consent (session setup).
Sources: World Bank, IMF (proxy), UN SDG (proxy), Export Controls.
Each source loads in its own tab to avoid heavy all-at-once API calls.
"""
import uuid

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.loaders import (
    get_many_indicators,
    latest_value,
    macro_snapshot,
    social_snapshot,
    trade_snapshot,
    get_export_control_snapshot,
    fetch_consolidated_screening_list,
    actor_to_iso3,
)
from engine.actors import get_actor_names
from storage.session_state import init_session_defaults, require_auth

st.set_page_config(
    page_title="Auracelle Charlie — Real-World Data Metrics",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("<style>div.block-container{padding-top:0.6rem;}</style>", unsafe_allow_html=True)

init_session_defaults()
require_auth()

if not st.session_state.get("consent", False):
    st.warning("Session Setup is required before accessing Real-World Data Metrics.")
    st.switch_page("pages/01_Session_Setup.py")

st.title("🌍 Real-World Data Metrics")
st.caption(
    "World Bank + IMF (proxy) + UN SDG + Export Controls — "
    "integrated as contextual inputs for Charlie's stress-tests.\n\n"
    "Each source loads on demand in its own tab to avoid heavy all-at-once API calls."
)

ACTORS = get_actor_names()

# ── Research session ID ───────────────────────────────────────────────────────
if "research_session_id" not in st.session_state:
    st.session_state["research_session_id"] = str(uuid.uuid4())

# ── Policy selector — mirrors Simulation page + new policies ──────────────────
POLICY_OPTIONS = [
    "EU Artificial Intelligence Act (AI Act) - Regulation (EU) 2024/1689",
    "EU General Data Protection Regulation (GDPR) - Regulation (EU) 2016/679",
    "EU Digital Services Act (DSA) - Regulation (EU) 2022/2065",
    "EU NIS2 Directive - Directive (EU) 2022/2555",
    "UNESCO Recommendation on the Ethics of Artificial Intelligence (2021)",
    "OECD Recommendation of the Council on Artificial Intelligence (OECD AI Principles, 2019)",
    "American AI Action Plan",
    "NATO Article 5",
    "Political Declaration on Responsible Military Use of Artificial Intelligence and Autonomy (2023)",
    "U.S. Department of Defense Directive 3000.09 - Autonomy in Weapon Systems",
    "NATO Revised AI Strategy (2024) + Data Quality Framework for the Alliance",
    "U.S. BIS Export Administration Regulations - Advanced Computing, AI Model Weights, and Semiconductor Controls",
]

# Resolve from session state if Simulation page has already set a policy
def _get_policy_from_session(default: str = POLICY_OPTIONS[0]) -> str:
    for key in ("selected_policy", "policy_selected", "policy_scenario"):
        v = st.session_state.get(key)
        if v and v in POLICY_OPTIONS:
            return v
    return default

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    actor = st.selectbox("Select Actor", ACTORS, index=0)
    iso3 = actor_to_iso3(actor)
with col_d:
    _default_pol = _get_policy_from_session()
    _pol_idx = POLICY_OPTIONS.index(_default_pol) if _default_pol in POLICY_OPTIONS else 0
    policy_name = st.selectbox("Policy scenario", POLICY_OPTIONS, index=_pol_idx,
                               help="Used to contextualise stress-test outcomes alongside indicator data.")
    st.session_state["selected_policy"] = policy_name
with col_b:
    if not iso3:
        st.warning(f"No ISO3 code configured for {actor} — World Bank API calls will be skipped.")

with col_c:
    start_year, end_year = st.slider("Year range", 1990, 2024, (2010, 2024), step=1, key="rw_years")
    trade_year = st.slider("Trade year", 1990, 2024, 2024, step=1, key="rw_trade_year")

st.markdown(f"**Research Session ID:** `{st.session_state['research_session_id']}`")
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_wb, tab_macro, tab_sdg, tab_trade, tab_export = st.tabs([
    "🌐 World Bank",
    "💹 Macro (IMF proxy)",
    "🌱 UN SDG",
    "🔄 Trade",
    "🚫 Export Controls",
])

# ── World Bank tab ────────────────────────────────────────────────────────────
with tab_wb:
    st.subheader("World Bank Indicators")
    st.caption(f"Year range: {start_year}–{end_year} (adjust using the sliders above)")

    if st.button("Load World Bank Data", use_container_width=True, key="wb_load"):
        if not iso3:
            st.error("No ISO3 code — cannot query World Bank API.")
        else:
            with st.spinner(f"Fetching World Bank data for {actor} ({iso3})…"):
                data = get_many_indicators([iso3], start_year=start_year, end_year=end_year)

            for label, df in data.items():
                if df.empty:
                    st.warning(f"{label}: no data returned.")
                    continue
                df_clean = df.dropna(subset=["Value"]).copy()
                if df_clean.empty:
                    st.warning(f"{label}: all values null.")
                    continue
                df_clean["Year"] = df_clean["Year"].astype(str).str.replace("YR", "").astype(int)
                fig = px.line(df_clean, x="Year", y="Value", title=label, markers=True)
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=35, b=0))
                st.plotly_chart(fig, use_container_width=True)

            # Data provenance
            with st.expander("📚 Data provenance", expanded=False):
                st.markdown("""
- **World Bank API** (wbgapi): [docs](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- **Indicators**: GDP (NY.GDP.MKTP.CD), Military Expenditure (MS.MIL.XPND.GD.ZS),
  Internet Users (IT.NET.USER.ZS), Trade % GDP (NE.TRD.GNFS.ZS),
  Inflation CPI (FP.CPI.TOTL.ZG), R&D Expenditure (GB.XPD.RSDV.GD.ZS)
""")

# ── Macro tab ─────────────────────────────────────────────────────────────────
with tab_macro:
    st.subheader("Macro Snapshot (IMF WEO proxy)")
    if st.button("Load Macro Snapshot", use_container_width=True, key="macro_load"):
        if not iso3:
            st.error("No ISO3 code.")
        else:
            with st.spinner("Loading macro snapshot…"):
                snap = macro_snapshot(iso3)
            col_a, col_b = st.columns(2)
            col_a.metric("GDP (USD trillions)", f"{snap.get('GDP_USD_trillions') or '—'}")
            col_b.info(snap.get("note", ""))
            st.caption(f"Source: {snap.get('source', 'World Bank proxy')}")

# ── UN SDG tab ────────────────────────────────────────────────────────────────
with tab_sdg:
    st.subheader("UN SDG Indicators (proxy)")
    if st.button("Load SDG Snapshot", use_container_width=True, key="sdg_load"):
        if not iso3:
            st.error("No ISO3 code.")
        else:
            with st.spinner("Loading SDG snapshot…"):
                snap = social_snapshot(iso3)
            col_a, col_b = st.columns(2)
            col_a.metric("Internet Penetration (%)", snap.get("internet_penetration_pct") or "—")
            col_b.caption(f"Source: {snap.get('source', 'World Bank')}")

# ── Trade tab ─────────────────────────────────────────────────────────────────
with tab_trade:
    st.subheader("Trade Data (Comtrade proxy)")
    st.caption(f"Trade year: {trade_year} (adjust using the slider above)")
    if st.button("Load Trade Snapshot", use_container_width=True, key="trade_load"):
        if not iso3:
            st.error("No ISO3 code.")
        else:
            with st.spinner("Loading trade snapshot…"):
                snap = trade_snapshot(iso3, year=trade_year)
            col_a, col_b = st.columns(2)
            col_a.metric("Trade (% of GDP)", snap.get("trade_pct_gdp") or "—")
            col_b.caption(f"Year: {snap.get('year')} | Source: {snap.get('source', 'World Bank proxy')}")
            st.info("Full UN Comtrade partner breakdown requires a Comtrade subscription key.")

# ── Export Controls tab ───────────────────────────────────────────────────────
with tab_export:
    st.subheader("US Export Controls / Consolidated Screening List")
    if st.button("Load Export Controls Data", use_container_width=True, key="export_load"):
        with st.spinner("Fetching Consolidated Screening List…"):
            df = fetch_consolidated_screening_list()
        if df.empty:
            st.warning(
                "CSL API returned no data. The trade.gov API may require authentication "
                "or the endpoint may be temporarily unavailable."
            )
        else:
            st.metric("Total screened entities", len(df))
            if "country" in df.columns:
                top = df["country"].value_counts().head(15).reset_index()
                top.columns = ["Country", "Entity Count"]
                fig = px.bar(top, x="Country", y="Entity Count", title="Top 15 Countries by Screened Entities")
                fig.update_layout(height=350, margin=dict(l=0, r=0, t=35, b=0))
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df.head(50), use_container_width=True)

        with st.expander("📚 Data provenance", expanded=False):
            st.markdown("""
- **US Consolidated Screening List (CSL)**: trade.gov API
- Includes: Entity List, Denied Persons List, Unverified List (BIS);
  OFAC SDN; State AECA Debarred; and others.
""")


# Helper to avoid import error if get_export_control_snapshot not yet implemented
def get_export_control_snapshot(iso3: str) -> dict:
    df = fetch_consolidated_screening_list()
    if df.empty or "country" not in df.columns:
        return {"count": 0, "source": "CSL"}
    from engine.actors import get_iso3_map
    # reverse ISO3 to country name for matching
    counts = df["country"].value_counts().to_dict()
    return {"count": counts.get(iso3, 0), "source": "CSL", "all_counts": counts}
