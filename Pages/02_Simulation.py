"""
pages/02_Simulation.py — Core policy stress-testing wargame.

Gated by: authentication + session setup.
Imports: engine, adjudication, data, storage — no inline RL or DB code.
"""
import os
import json
import textwrap
import uuid

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from adjudication.policy_owner import PolicyOwner
from data.loaders import (
    get_latest_gdp,
    get_latest_military_expenditure,
    get_internet_penetration,
    fetch_consolidated_screening_list,
    get_sanctioned_countries,
)
from engine.actors import load_actor_profiles, get_actor_names, get_iso3_map
from engine.scoring import compute_systemic_risk
from storage.research_store import init_db, log_move, set_outcomes, upsert_session
from storage.session_state import init_session_defaults, require_auth, require_setup

st.set_page_config(
    page_title="Auracelle Charlie 3 — Policy Stress-Testing Wargame",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_defaults()
require_auth()
require_setup()
init_db()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
upsert_session(
    st.session_state["session_id"],
    scenario=st.session_state.get("scenario"),
    condition_tag=st.session_state.get("condition_tag"),
)

# ── Adjudicator ───────────────────────────────────────────────────────────────
if st.session_state.get("adjudicator") is None:
    st.session_state["adjudicator"] = PolicyOwner(mode="neutral")
adjudicator: PolicyOwner = st.session_state["adjudicator"]

# ── Actor baseline data ───────────────────────────────────────────────────────
raw_profiles = load_actor_profiles()
country_options = get_actor_names()
country_to_iso = get_iso3_map()

# Build working data dict (mutable, overwritten by WB API below)
default_data: dict = {
    name: {
        "gdp":               d["gdp"],
        "influence":         d["influence"],
        "position":          d["position"],
        "mil_exp":           d["mil_exp"],
        "internet":          d["internet"],
        "cultural_alignment": d["cultural_alignment"],
    }
    for name, d in raw_profiles.items()
}

# ── Sidebar — real-world data controls ───────────────────────────────────────
with st.sidebar:
    st.header("🌍 Real-World Data Integration")
    if st.button("🔄 Refresh API Data"):
        st.session_state["api_data_loaded"] = False
        st.rerun()
    st.markdown("---")
    st.markdown("**Data Sources:**")
    st.markdown("- World Bank API ✅")
    st.markdown("- US Export Controls ✅")
    st.markdown("- SIPRI (CSV Upload)")
    sipri_file = st.file_uploader("Upload SIPRI CSV", type=["csv"])

    with st.expander("📊 Data & Evidence Sources", expanded=False):
        st.markdown("""
- **World Bank (wbgapi)**: GDP, military expenditure, internet penetration.
- **U.S. Consolidated Screening List (CSL)**: export-control / sanctions screening.
- **SIPRI (upload)**: defence / military expenditure reference data (CSV upload).

When a score, recommendation, or warning is shown, it is attributable to one or
more of these sources plus the transformations applied inside the sandbox.
""")

# ── Load real-world data ──────────────────────────────────────────────────────
if not st.session_state.get("api_data_loaded", False):
    with st.spinner("🌍 Loading real-world data from APIs…"):
        for country, iso3 in country_to_iso.items():
            if country not in default_data:
                continue
            try:
                gdp = get_latest_gdp(iso3)
                mil = get_latest_military_expenditure(iso3)
                inet = get_internet_penetration(iso3)
                if gdp is not None:
                    default_data[country]["gdp"] = round(float(gdp), 2)
                if mil is not None:
                    default_data[country]["mil_exp"] = round(float(mil), 2)
                if inet is not None:
                    default_data[country]["internet"] = round(float(inet), 1)
                adjudicator.integrate_real_world_data(
                    iso3,
                    gdp=default_data[country]["gdp"],
                    mil_exp=default_data[country]["mil_exp"],
                    internet=default_data[country]["internet"],
                )
            except Exception:
                pass
        try:
            sanctioned = get_sanctioned_countries()
            for country, iso3 in country_to_iso.items():
                label = "United Arab Emirates" if country == "Dubai" else country
                count = sanctioned.get(label, 0)
                adjudicator.integrate_real_world_data(iso3, sanctions=count)
        except Exception:
            pass
        st.session_state["api_data_loaded"] = True

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🎯 Auracelle Charlie 3 — Policy Stress-Testing Wargame")
st.header("Auracelle Charlie 3 — War Gaming Stress-Testing Policy Governance Research Simulation/Prototype")

# ── Policy selection ──────────────────────────────────────────────────────────
import yaml
from pathlib import Path

_POLICIES_YAML = Path(__file__).parent.parent / "config" / "policies.yaml"
with open(_POLICIES_YAML) as fh:
    _pol_cfg = yaml.safe_load(fh)
policy_options  = [p["label"] for p in _pol_cfg["policies"]]
policy_briefs   = {p["label"]: p["brief"] for p in _pol_cfg["policies"]}

selected_policy = st.selectbox("Select Policy Scenario", policy_options)
st.caption("Scenario brief")
st.info(policy_briefs.get(selected_policy, ""))

# ── Actor selection ───────────────────────────────────────────────────────────
selected_country_a = st.selectbox("Select Country A", country_options, index=0)
selected_country_b = st.selectbox("Select Country B", country_options, index=1)

role_tags = [
    "Governance", "MilitaryAI", "DataPrivacy", "ExportControl",
    "Diplomacy", "StandardSetting", "Surveillance", "Trade", "TechAlliance",
]
role_country_a = st.selectbox(f"Role for {selected_country_a}", role_tags, key="role_a")
role_country_b = st.selectbox(f"Role for {selected_country_b}", role_tags, key="role_b")
player_country  = st.selectbox("🎖️ You represent:", country_options, index=0)

# ── Policy Owner (narrative) ─────────────────────────────────────────────────
def _heuristic_po_narrative(policy, country, objections, concessions, aggressiveness):
    conc = ", ".join(concessions) if concessions else "limited targeted concessions"
    obj  = objections.strip() or "No explicit objections provided yet."
    tone = {"Low": "measured, collaborative", "Medium": "firm but constructive",
            "High": "hard-nosed, stability-first"}.get(aggressiveness, "measured")
    return textwrap.dedent(f"""
    **Policy Owner Narrative (heuristic mode)**
    - **Policy frame:** {policy}
    - **You represent:** {country}  |  **Tone:** {tone}

    **Acknowledgement**
    Core concerns heard: {obj}

    **Response**
    Objective: preserve legitimate national interests while preventing compliance gaming,
    trust collapse, and coalition fracture.

    **Concessions on offer**
    - {conc}
    - Sequencing: pilot → review gate → scale only if metrics improve
    - Confidential channels where disclosure creates security exposure

    **Non-negotiables**
    - Minimum baseline assurance for high-risk frontier capabilities
    - Clear accountability for violations (graduated, not arbitrary)
    - Mutual transparency sufficient to deter gaming

    **Ask back**
    What clause or mechanism would shift you from hedge/oppose to support while keeping the policy enforceable?
    """).strip()


def _openai_chat(messages, max_tokens=650):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": os.getenv("AURACELLE_OPENAI_MODEL", "gpt-4o-mini"),
                  "messages": messages, "temperature": 0.4, "max_tokens": max_tokens},
            timeout=30,
        )
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def generate_po_narrative(policy, country, objections, concessions, aggressiveness):
    system = (
        "You are the Policy Owner in an AI governance wargaming workshop. "
        "Respond to objections preserving policy intent, offering pragmatic concessions, "
        "identifying non-negotiables. Do NOT rewrite the full policy text."
    )
    user = (
        f"Policy: {policy}\nActor: {country}\nAggressiveness: {aggressiveness}\n"
        f"Objections:\n{objections}\nConcessions menu:\n{json.dumps(concessions)}\n\n"
        "Produce: 5-8 talking points; 3 pragmatic concessions with rationale; "
        "3 non-negotiables; 1-paragraph closing statement."
    )
    out = _openai_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return out or _heuristic_po_narrative(policy, country, objections, concessions, aggressiveness)


with st.expander("🧭 Policy Owner (Narrative) — respond to objections", expanded=False):
    st.caption("Generates negotiation posture. Text amendments are handled on the Policy Stress Testing Platform page.")
    po_mode       = st.radio("Policy Owner Mode", ["Manual", "Agentic AI"], horizontal=True, key="po_mode")
    aggressiveness = st.select_slider("Stance aggressiveness", ["Low", "Medium", "High"], value="Medium", key="po_aggr")
    concessions_menu = [
        "Narrow scope to threshold models",
        "Mutual recognition audits",
        "Safe harbor for incident reporting",
        "Confidential reporting channel",
        "Graduated enforcement ladder",
        "Capacity-building support package",
        "Pilot-first with review gate",
        "Regional implementation first",
        "Explicit national security carve-out (narrow)",
        "Private-sector compliance credits / incentives",
    ]
    selected_concessions = st.multiselect("Concessions menu", concessions_menu, default=["Pilot-first with review gate"])
    objections_txt = st.text_area("Objections to address (paste notes from Country Leads)", height=140, key="po_objections")

    if po_mode == "Manual":
        st.info("Manual mode: type your own narrative response below.")
        manual_resp = st.text_area("Your Policy Owner narrative response", height=180, key="po_manual_resp")
        if st.button("Save manual response", key="po_save_manual"):
            st.session_state["po_narrative_output"] = manual_resp.strip()
    else:
        if st.button("Generate narrative response (Agentic)", key="po_generate"):
            st.session_state["po_narrative_output"] = generate_po_narrative(
                selected_policy, player_country, objections_txt, selected_concessions, aggressiveness
            )

    if st.session_state.get("po_narrative_output"):
        st.markdown("### Policy Owner Output")
        st.markdown(st.session_state["po_narrative_output"])

# ── Round controls ────────────────────────────────────────────────────────────
round_col1, round_col2, round_col3 = st.columns(3)
with round_col1:
    st.subheader(f"🕐 Round: {st.session_state['round']}")
with round_col2:
    st.session_state["episode_length"] = st.slider(
        "Episode Length (rounds)", 1, 30, st.session_state.get("episode_length", 5),
        key="episode_length_slider",
    )
with round_col3:
    st.session_state["stochastic_exploration"] = st.toggle(
        "Enable Stochastic Exploration",
        value=st.session_state.get("stochastic_exploration", False),
        help="Introduces variability into reward and risk calculations.",
        key="stochastic_toggle",
    )

# ── Alignment / reward / risk ─────────────────────────────────────────────────
alignment_score = float(st.session_state.get("alignment_score", 0.5))

adj_state = st.session_state.get("adjudication_state")
if not isinstance(adj_state, dict):
    adj_state = {"tension_index": 0.5, "confidence_score": 0.7,
                 "status": "not evaluated", "notes": ""}
    st.session_state["adjudication_state"] = adj_state

base_reward = (
    alignment_score * 0.5
    + (1.0 - adj_state["tension_index"]) * 0.3
    + adj_state["confidence_score"] * 0.2
)
if st.session_state.get("stochastic_exploration"):
    base_reward = float(np.clip(base_reward + np.random.normal(0, 0.05), 0, 1))

reward = float(base_reward)
risk   = float(adj_state["tension_index"])

# Log round metrics
st.session_state["round_metrics_trace"].append({
    "round":      int(st.session_state["round"]),
    "reward":     reward,
    "risk":       risk,
    "tension":    float(adj_state["tension_index"]),
    "confidence": float(adj_state["confidence_score"]),
    "alignment":  float(alignment_score),
})

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("🏆 Reward", f"{reward * 100:.1f}")
with m2:
    st.metric("⚠️ Risk", f"{risk * 100:.1f}")
with m3:
    ep_pos = (st.session_state["round"] - 1) % st.session_state["episode_length"] + 1
    st.metric("📏 Episode Progress", f"{ep_pos}/{st.session_state['episode_length']}")

nav1, nav2 = st.columns(2)
with nav1:
    if st.button("▶️ Next Round"):
        log_move(
            session_id=st.session_state.get("session_id"),
            participant_id=st.session_state.get("participant_id"),
            round_num=st.session_state.get("round"),
            policy=selected_policy,
            action="next_round",
            notes="",
            state_json=json.dumps({"reward": reward, "risk": risk}),
        )
        st.session_state["round"] += 1
        st.rerun()
with nav2:
    if st.button("🔄 Reset Episode"):
        st.session_state["round"] = 1
        st.session_state["round_metrics_trace"] = []
        st.rerun()

# ── Adjudicator status ────────────────────────────────────────────────────────
st.subheader("🤖 AI Agentic Adjudicator Status")

actor_beliefs   = {selected_country_a: default_data[selected_country_a]["position"],
                   selected_country_b: default_data[selected_country_b]["position"]}
power_levels    = {selected_country_a: default_data[selected_country_a]["influence"],
                   selected_country_b: default_data[selected_country_b]["influence"]}
alignment_graph = {f"{selected_country_a}:{selected_country_b}": alignment_score}

tension = adjudicator.calculate_tension_index(actor_beliefs, power_levels, alignment_graph)
shock   = adjudicator.inject_shock(st.session_state["round"], tension)

# Update state
adj_state["tension_index"] = tension
adj_state["confidence_score"] = float(np.clip(1.0 - tension * 0.5, 0, 1))
st.session_state["adjudication_state"] = adj_state

c1, c2, c3, c4 = st.columns(4)
with c1:
    color = "🔴" if tension > 0.7 else ("🟡" if tension > 0.4 else "🟢")
    st.metric(f"{color} Tension", f"{tension * 100:.1f}%")
with c2:
    st.metric("🎲 Confidence", f"{adj_state['confidence_score'] * 100:.1f}%")
with c3:
    st.metric("📊 Alignment", f"{alignment_score * 100:.0f}%")
with c4:
    st.metric("✅ Real Data", "Active" if adjudicator.real_world_data else "Baseline")

# Deception detection
st.markdown("### 🎭 Deception Detection")
deception_data = []
for actor in [selected_country_a, selected_country_b]:
    score = adjudicator.detect_deception(
        default_data[actor]["position"],
        [],  # historical actions would come from session moves in a full implementation
        default_data[actor]["influence"],
    )
    deception_data.append({
        "Actor":  actor,
        "Risk":   f"{score * 100:.1f}%",
        "Status": "⚠️ Suspicious" if score > 0.5 else "✅ Consistent",
    })
st.dataframe(pd.DataFrame(deception_data), use_container_width=True)

# Shock display
if shock:
    st.warning(f"💥 **EXTERNAL SHOCK**\n\n{shock['description']}")
    st.session_state["event_log"].append(shock)
else:
    narrative = adjudicator.generate_round_narrative(
        st.session_state["round"], {}, adj_state, selected_policy
    )
    st.info(f"ℹ️ {narrative}")

# ── Policy Position Comparison ────────────────────────────────────────────────
st.subheader("🆚 Policy Position Comparison (Real-World Data)")

d_a = default_data[selected_country_a]
d_b = default_data[selected_country_b]

comparison_df = pd.DataFrame({
    "Metric": ["GDP (Trillion USD)", "Military Exp (% GDP)", "Internet Penetration (%)",
               "Influence Score", "AI Policy Position"],
    selected_country_a: [
        f"${d_a['gdp']:.2f}T", f"{d_a['mil_exp']:.1f}%",
        f"{d_a['internet']:.1f}%", d_a["influence"], d_a["position"],
    ],
    selected_country_b: [
        f"${d_b['gdp']:.2f}T", f"{d_b['mil_exp']:.1f}%",
        f"{d_b['internet']:.1f}%", d_b["influence"], d_b["position"],
    ],
})
st.table(comparison_df)

player_new_position = st.text_input(
    "📜 Propose New Policy Position",
    value=default_data[player_country]["position"],
)
opponent_country = selected_country_b if player_country == selected_country_a else selected_country_a
alignment_score = 1.0 if player_new_position == default_data[opponent_country]["position"] else 0.0
st.session_state["alignment_score"] = float(alignment_score)

st.markdown("---")

# ── Strategic analysis ────────────────────────────────────────────────────────
st.subheader("🎯 Strategic Analysis & Recommendations")

col_l, col_r = st.columns(2)
gdp_ratio = d_a["gdp"] / (d_b["gdp"] + 0.01)

for col, actor, data, ratio_dir in [
    (col_l, selected_country_a, d_a, gdp_ratio),
    (col_r, selected_country_b, d_b, 1 / gdp_ratio),
]:
    with col:
        st.markdown(f"**{actor} Assessment**")
        if ratio_dir > 2.0:
            st.success(f"✅ Strong economic advantage ({ratio_dir:.1f}× GDP)")
        elif ratio_dir < 0.5:
            st.warning(f"⚠️ Economic disadvantage ({ratio_dir:.1f}× GDP)")
        else:
            st.info(f"📊 Comparable economic power ({ratio_dir:.1f}× GDP)")

        if data["mil_exp"] > 3.0:
            st.warning(f"⚠️ High military expenditure ({data['mil_exp']:.1f}% GDP)")
        elif data["mil_exp"] < 1.5:
            st.info(f"🕊️ Low military expenditure ({data['mil_exp']:.1f}% GDP)")
        else:
            st.success(f"✅ Moderate military spending ({data['mil_exp']:.1f}% GDP)")

        if data["internet"] > 90:
            st.success(f"✅ Advanced digital infrastructure ({data['internet']:.0f}%)")
        elif data["internet"] < 60:
            st.warning(f"⚠️ Limited digital infrastructure ({data['internet']:.0f}%)")
        else:
            st.info(f"📊 Developing digital infrastructure ({data['internet']:.0f}%)")

st.markdown("#### 🤖 Adjudicator Recommendations")
if tension > 0.7:
    st.error("**🔴 CRITICAL TENSION** — Immediate de-escalation recommended. Risk of shock: HIGH.")
elif tension > 0.4:
    st.warning("**🟡 ELEVATED TENSION** — Monitor closely. Risk of shock: MODERATE.")
else:
    st.success("**🟢 STABLE** — Diplomatic environment conducive to cooperation.")

# ── Round metrics trace chart ─────────────────────────────────────────────────
if len(st.session_state["round_metrics_trace"]) > 1:
    st.markdown("---")
    st.subheader("📈 Session Metrics Trace")
    trace_df = pd.DataFrame(st.session_state["round_metrics_trace"])
    fig = go.Figure()
    for col in ["reward", "risk", "tension", "alignment"]:
        if col in trace_df.columns:
            fig.add_trace(go.Scatter(x=trace_df["round"], y=trace_df[col], name=col.title(), mode="lines+markers"))
    fig.update_layout(
        xaxis_title="Round", yaxis_title="Score (0–1)",
        legend=dict(orientation="h"), margin=dict(l=0, r=0, t=30, b=0),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Persist outcomes ──────────────────────────────────────────────────────────
try:
    set_outcomes(
        session_id=st.session_state.get("session_id", ""),
        trust=float(np.clip(adj_state["confidence_score"] * (1 - tension * 0.5), 0, 1)),
        compliance=float(alignment_score),
        alignment=float(alignment_score),
        resilience=float(np.clip(adj_state["confidence_score"] * (1 - tension * 0.3), 0, 1)),
    )
except Exception:
    pass
