# SPDX-License-Identifier: MIT
import os
import uuid
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Auracelle Charlie - Real World Data (API v2)", layout="wide")

st.title("Real-World Data Metrics (FastAPI Backend v2)")
st.caption(
    "Backend schema v2 adds time-series + trade partners so we can render KPIs -> trends -> Sankey -> map -> policy overlay. "
    "Visuals prioritize *flagged* partners (sanctions/export controls/high tariffs)."
)

ACTORS = [
    "US", "UK", "Dubai", "Japan", "China", "Brazil", "India", "NATO",
    "Israel", "Paraguay", "Belgium", "Denmark", "Ukraine", "Serbia", "Argentina",
    "Norway", "Switzerland", "Poland", "Global South"
]

ACTOR_TO_ISO3 = {
    "US": "USA",
    "UK": "GBR",
    "Dubai": "ARE",          # proxy for UAE
    "Japan": "JPN",
    "China": "CHN",
    "Brazil": "BRA",
    "India": "IND",
    "NATO": "NATO",
    "Israel": "ISR",
    "Paraguay": "PRY",
    "Belgium": "BEL",
    "Denmark": "DNK",
    "Ukraine": "UKR",
    "Serbia": "SRB",
    "Argentina": "ARG",
    "Norway": "NOR",
    "Switzerland": "CHE",
    "Poland": "POL",
    "Global South": "LMY",   # WB aggregate: Low & middle income
}

def get_base_url(default="http://localhost:8000"):
    # Streamlit raises StreamlitSecretNotFoundError when secrets.toml doesn't exist.
    # Gracefully fall back to env var or default.
    try:
        return st.secrets.get("AURACELLE_API_BASE", os.environ.get("AURACELLE_API_BASE", default))
    except Exception:
        return os.environ.get("AURACELLE_API_BASE", default)

BASE_URL = get_base_url()

POSSIBLE_POLICY_KEYS = [
    "policy_scenario", "policy_selected", "selected_policy",
    "policy", "policy_name", "scenario_policy"
]

def get_policy_from_session(default="AI Data Localization"):
    for k in POSSIBLE_POLICY_KEYS:
        if k in st.session_state and st.session_state[k]:
            return str(st.session_state[k])
    return default

colA, colB, colC, colD = st.columns([1.2, 1.0, 1.0, 1.2])
with colA:
    actor = st.selectbox("Select Actor", ACTORS, index=0)
with colB:
    start_year, end_year = st.slider("Year Range", 1990, 2024, (2010, 2024))
with colC:
    trade_year = st.slider("Trade Year", 1990, 2024, 2024)
with colD:
    options = ["AI Data Localization", "Export Controls Tightening"]
    default_policy = get_policy_from_session(default=options[0])
    idx = options.index(default_policy) if default_policy in options else 0
    policy_name = st.selectbox("Stress Test Outcomes", options, index=idx)
    st.caption("Mirrors Simulation Policy Scenario when available.")

session_id = st.session_state.get("research_session_id") or str(uuid.uuid4())
st.session_state["research_session_id"] = session_id
st.write(f"Research Session ID: {session_id}")

q = st.text_input("CSL test query", value="bank")

def post_metrics():
    payload = {
        "actor": actor,
        "iso3": ACTOR_TO_ISO3.get(actor, "USA"),
        "start_year": int(start_year),
        "end_year": int(end_year),
        "trade_year": int(trade_year),
        "csl_query": q,
        "policy": policy_name,
        "flagged_only": True,
        "max_partners": 12,
        "session_id": session_id,
    }
    r = requests.post(f"{BASE_URL}/v2/metrics", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()

def _safe_num(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def render_kpis(wb_latest: dict, imf: dict):
    col1, col2, col3, col4, col5 = st.columns(5)
    gdp = _safe_num(wb_latest.get("GDP (current US$)"))
    pop = _safe_num(wb_latest.get("Population, total"))
    inet = _safe_num(wb_latest.get("Internet Users (% of population)"))
    mil = _safe_num(wb_latest.get("Military Expenditure (% of GDP) (SIPRI)"))
    debt = _safe_num(imf.get("debt_gdp_pct"))

    col1.metric("GDP (US$)", f"{gdp:,.0f}" if gdp else "—")
    col2.metric("Population", f"{pop:,.0f}" if pop else "—")
    col3.metric("Internet Users (%)", f"{inet:.1f}" if inet else "—")
    col4.metric("Mil Exp (% GDP)", f"{mil:.2f}" if mil else "—")
    col5.metric("Debt/GDP (%)", f"{debt:.1f}" if debt else "—")

def render_trends(wb_series: dict):
    st.subheader("Trends (World Bank time series)")
    if not wb_series:
        st.info("No time series returned yet.")
        return

    indicator = st.selectbox("Indicator", list(wb_series.keys()), index=0)
    series = wb_series.get(indicator, {})
    if not series:
        st.info("Selected indicator has no series.")
        return
    df = pd.DataFrame({"year": list(series.keys()), "value": list(series.values())}).sort_values("year")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    if df.empty:
        st.info("Series is empty after cleaning nulls.")
        return
    st.line_chart(df.set_index("year"))

def render_sankey(trade: dict):
    st.subheader("Trade Flows (Flagged partners prioritized)")
    exports = (trade or {}).get("exports_by_partner", []) or []
    imports = (trade or {}).get("imports_by_partner", []) or []
    note = (trade or {}).get("note") or ""

    if not exports and not imports:
        st.info("No partner flows returned yet. (Comtrade partner breakdown may be empty.)")
        if note:
            st.caption(note)
        return

    actor_node = ACTOR_TO_ISO3.get(actor, "USA")
    partners = sorted({x.get("partner_iso3") for x in (exports + imports) if x.get("partner_iso3")})
    nodes = [actor_node] + partners
    idx = {n:i for i,n in enumerate(nodes)}

    sources, targets, values = [], [], []
    for row in exports:
        p = row.get("partner_iso3"); v = row.get("usd")
        if p and v:
            sources.append(idx[actor_node]); targets.append(idx[p]); values.append(float(v))
    for row in imports:
        p = row.get("partner_iso3"); v = row.get("usd")
        if p and v:
            sources.append(idx[p]); targets.append(idx[actor_node]); values.append(float(v))

    if not values:
        st.info("Flows exist but are all null/zero after cleaning.")
        if note:
            st.caption(note)
        return

    fig = go.Figure(data=[go.Sankey(
        node=dict(label=nodes, pad=15, thickness=18),
        link=dict(source=sources, target=targets, value=values),
    )])
    st.plotly_chart(fig, use_container_width=True)
    if note:
        st.caption(note)

def render_map(trade: dict, flags: dict):
    st.subheader("Partner Risk Map (Flagged only)")
    flags = flags or {}
    flagged = set(flags.get("flagged_iso3", []) or [])

    exports = (trade or {}).get("exports_by_partner", []) or []
    imports = (trade or {}).get("imports_by_partner", []) or []

    vols = {}
    for row in exports:
        p = row.get("partner_iso3"); v = row.get("usd") or 0
        if p: vols[p] = vols.get(p, 0) + float(v or 0)
    for row in imports:
        p = row.get("partner_iso3"); v = row.get("usd") or 0
        if p: vols[p] = vols.get(p, 0) + float(v or 0)

    partners = sorted(flagged) if flagged else sorted(vols.keys())
    if not partners:
        st.info("No partner countries available to map yet.")
        return

    df = pd.DataFrame([{"iso3": p, "trade_usd": vols.get(p, 0), "flagged": p in flagged} for p in partners])
    fig = px.choropleth(df, locations="iso3", color="trade_usd", hover_data=["flagged"],
                        title="Trade volume for flagged partners (or fallback partners)")
    st.plotly_chart(fig, use_container_width=True)

def render_policy_overlay(policy_overlay: dict, flags: dict):
    policy_name = (policy_overlay or {}).get("policy_name") or "Unknown"
    outcomes = (policy_overlay or {}).get("outcomes") or {}
    st.subheader("Stress Test Outcomes")
    st.caption("Data-driven heuristics (not a predictive oracle). Outcomes update as additional flag datasets (sanctions/tariffs/culture) come online.")

    if outcomes:
        risk = outcomes.get("risk_score")
        reward = outcomes.get("reward_score")
        horizon = outcomes.get("horizon")
        conf = outcomes.get("confidence")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk score (0-100)", "—" if risk is None else f"{risk:.0f}")
        c2.metric("Reward score (0-100)", "—" if reward is None else f"{reward:.0f}")
        c3.metric("Time horizon", horizon or "—")
        c4.metric("Confidence", conf or "—")

        # Gauge
        if risk is not None or reward is not None:
            fig = go.Figure()
            if risk is not None:
                fig.add_trace(go.Indicator(mode="gauge+number", value=float(risk), title={"text": "Risk"}, domain={"x": [0, 0.48], "y": [0, 1]}))
            if reward is not None:
                fig.add_trace(go.Indicator(mode="gauge+number", value=float(reward), title={"text": "Reward"}, domain={"x": [0.52, 1], "y": [0, 1]}))
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        risks = outcomes.get("key_risks", []) or []
        mitigations = outcomes.get("mitigations", []) or []
        recs = outcomes.get("foresight_recommendations", []) or []

        cL, cR = st.columns(2)
        with cL:
            st.markdown("**Key risks**")
            if risks:
                for r in risks:
                    st.write(f"- {r}")
            else:
                st.write("—")
        with cR:
            st.markdown("**Mitigations**")
            if mitigations:
                for r in mitigations:
                    st.write(f"- {r}")
            else:
                st.write("—")

        st.markdown("**Foresight recommendations**")
        if recs:
            for r in recs:
                st.write(f"- {r}")
        else:
            st.write("—")

    else:
        flagged = (flags or {}).get("flagged_iso3", []) or []
        if policy_name == "AI Data Localization":
            st.write("- Expected pressure: services trade friction up; data-transfer compliance cost up; partner coordination complexity up.")
        else:
            st.write("- Expected pressure: export/import constraints up; enforcement intensity up; partner substitution pressure up.")
        st.write(f"- Flagged partners count: {len(flagged)}")

if st.button("Run Metrics via Backend (v2)", type="primary"):
    try:
        payload = post_metrics()
        st.success("Backend responded successfully.")
    except Exception as e:
        st.error(f"Backend connection failed: {e}")
        st.stop()

    wb_latest = payload.get("worldbank", {}).get("latest", {}) or {}
    wb_series = payload.get("worldbank", {}).get("series", {}) or {}
    imf = payload.get("imf", {}) or {}
    trade = payload.get("trade", {}) or {}
    flags = payload.get("flags", {}) or {}

    render_kpis(wb_latest, imf)
    render_trends(wb_series)
    render_sankey(trade)
    render_map(trade, flags)
    render_policy_overlay(payload.get('policy_overlay', {}), flags)
