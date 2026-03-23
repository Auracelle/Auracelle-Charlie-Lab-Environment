import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
sys.path.insert(0, ".")
from adjudicator import AgenticAdjudicator
from agpo_data.research_store import init_db, log_move, set_outcomes, upsert_session


# Import AGPO data modules
try:
    from agpo_data.worldbank import get_latest_gdp, get_latest_military_expenditure, get_internet_penetration, get_many_indicators
    from agpo_data.exportcontrol import fetch_consolidated_screening_list, get_sanctioned_countries
    from agpo_data.sipri import parse_sipri_csv
    AGPO_AVAILABLE = True
except ImportError as e:
    st.warning(f"AGPO modules not fully loaded: {e}")
    AGPO_AVAILABLE = False

st.set_page_config(page_title="Auracelle Charlie 3 - War Gaming Stress-Testing Policy Governance Research Simulation/Prototype", layout="wide", initial_sidebar_state="collapsed")

init_db()
import uuid
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
upsert_session(st.session_state["session_id"], scenario=st.session_state.get("scenario"), condition_tag=st.session_state.get("condition_tag"))


if not st.session_state.get("authenticated", False):
    st.warning("Please log in first.")
    st.switch_page("app.py")

if not st.session_state.get("setup_complete", False):
    st.info("Please complete Session Setup before entering the simulation.")
    st.switch_page("pages/1_Session_Setup.py")


st.title("🎯 Auracelle Charlie 3 - Policy Stress-Testing Wargame")

st.header("Auracelle Charlie 3 - War Gaming Stress-Testing Policy Governance Research Simulation/Prototype")




# Initialize session state
if "round" not in st.session_state:
    st.session_state["round"] = 1
if "q_table" not in st.session_state:
    st.session_state["q_table"] = {}
if "adjudicator" not in st.session_state:
    st.session_state["adjudicator"] = AgenticAdjudicator(mode="neutral")
if "event_log" not in st.session_state:
    st.session_state["event_log"] = []
# New: round-level metrics and agent controls
if "round_metrics_trace" not in st.session_state:
    st.session_state["round_metrics_trace"] = []
if "episode_length" not in st.session_state:
    st.session_state["episode_length"] = 5
if "stochastic_exploration" not in st.session_state:
    st.session_state["stochastic_exploration"] = False
if "api_data_loaded" not in st.session_state:
    st.session_state["api_data_loaded"] = False

# Animation and click session state
if "animation_running" not in st.session_state:
    st.session_state["animation_running"] = False
if "selected_country_click" not in st.session_state:
    st.session_state["selected_country_click"] = None

adjudicator = st.session_state["adjudicator"]

# Sidebar for API Data Controls
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

    sipri_file = st.file_uploader("Upload SIPRI CSV", type=['csv'])

    with st.expander("📊 Data & Evidence Sources (Traceability)", expanded=False):
        st.markdown("""
- **World Bank (wbgapi)**: macro indicators (GDP, military expenditure, internet penetration) pulled via API.
- **U.S. Consolidated Screening List (CSL)**: export-control / sanctions screening via API wrapper.
- **SIPRI (upload)**: defense / military expenditure reference data (CSV upload).

**Interpretation:** When a score, recommendation, or warning is shown, it should be attributable to one or more of these sources
and the transformations applied inside the sandbox (metric → source → vintage/date → transformation → round/time).
""")



# Country mapping to ISO codes
country_to_iso = {
    "Dubai": "ARE", "United Kingdom": "GBR", "United States": "USA",
    "Japan": "JPN", "China": "CHN", "Brazil": "BRA", "India": "IND",
    "Greenland": "GRL", "Venezuela": "VEN"
}

policy_options = [
    "EU Artificial Intelligence Act (AI Act) - Regulation (EU) 2024/1689",
    "EU General Data Protection Regulation (GDPR) - Regulation (EU) 2016/679",
    "EU Digital Services Act (DSA) - Regulation (EU) 2022/2065",
    "EU NIS2 Directive - Directive (EU) 2022/2555",
    "UNESCO Recommendation on the Ethics of Artificial Intelligence (2021)",
    "OECD Recommendation of the Council on Artificial Intelligence (OECD AI Principles, 2019)",
    "American AI Action Plan",
    "NATO Article 5"
]
selected_policy = st.selectbox("Select Policy Scenario", policy_options)

policy_scenario_explanations = {
    "EU Artificial Intelligence Act (AI Act) - Regulation (EU) 2024/1689": "Risk-tiering, high-risk controls, governance obligations—perfect for stress-testing compliance, innovation tradeoffs, and cross-border adoption.",
    "EU General Data Protection Regulation (GDPR) - Regulation (EU) 2016/679": "The global reference point for privacy, data rights, and cross-border data governance (and it directly collides with AI training / data minimization debates).",
    "EU Digital Services Act (DSA) - Regulation (EU) 2022/2065": "Platform accountability and systemic-risk controls—useful for stress-testing content moderation, transparency, and disinformation pressures in a crisis.",
    "EU NIS2 Directive - Directive (EU) 2022/2555": "Cybersecurity governance obligations for critical and important entities—ideal for stress-testing incident response, resilience duties, and cross-border coordination under attack.",
    "UNESCO Recommendation on the Ethics of Artificial Intelligence (2021)": "A global ethical baseline for AI—useful for stress-testing value conflicts, implementation gaps, and alignment across diverse governance cultures.",
    "OECD Recommendation of the Council on Artificial Intelligence (OECD AI Principles, 2019)": "Widely adopted principles (robustness, transparency, accountability)—useful for stress-testing practical translation of norms into enforceable controls and incentives.",
    "American AI Action Plan": "A U.S.-anchored strategic blueprint for advancing AI while managing risks—useful for stress-testing national competitiveness vs safety, procurement, and cross-sector adoption tradeoffs.",
    "NATO Article 5": "Collective defense clause—useful for stress-testing alliance decision-making if AI-enabled cyber incidents or escalation pressures trigger collective response debates."
}

st.caption("Scenario brief")
st.info(policy_scenario_explanations.get(selected_policy, ""))
country_options = ["Dubai", "United Kingdom", "United States", "Japan", "China", "Brazil", "India", "Russia", "Iraq", "Qatar", "NATO", "Greenland", "Venezuela"]

# Default data structure
default_data = {
    "Dubai": {"gdp": 0.5, "influence": 0.7, "position": "Moderate regulatory stance", "mil_exp": 5.6, "internet": 99.0, "cultural_alignment": "Western-Middle East hybrid"},
    "United Kingdom": {"gdp": 3.2, "influence": 0.85, "position": "Supports EU-style data protection", "mil_exp": 2.2, "internet": 96.0, "cultural_alignment": "Western"},
    "United States": {"gdp": 21.0, "influence": 0.95, "position": "Favors innovation over regulation", "mil_exp": 3.4, "internet": 92.0, "cultural_alignment": "Western"},
    "Japan": {"gdp": 5.1, "influence": 0.88, "position": "Pro-regulation for trust", "mil_exp": 1.0, "internet": 95.0, "cultural_alignment": "Eastern-Western hybrid"},
    "China": {"gdp": 17.7, "influence": 0.93, "position": "Strict state-driven AI governance", "mil_exp": 1.7, "internet": 73.0, "cultural_alignment": "Eastern"},
    "Brazil": {"gdp": 2.0, "influence": 0.75, "position": "Leaning toward EU-style regulation", "mil_exp": 1.4, "internet": 81.0, "cultural_alignment": "Latin American"},
    "India": {"gdp": 3.7, "influence": 0.82, "position": "Strategic tech balancing", "mil_exp": 2.4, "internet": 43.0, "cultural_alignment": "South Asian"},
    "Russia": {"gdp": 1.8, "influence": 0.78, "position": "Sovereign tech control", "mil_exp": 4.3, "internet": 85.0, "cultural_alignment": "Eastern"},
    "Iraq": {"gdp": 0.2, "influence": 0.42, "position": "Developing governance framework", "mil_exp": 3.5, "internet": 49.0, "cultural_alignment": "Middle East"},
    "Qatar": {"gdp": 0.18, "influence": 0.68, "position": "Tech-forward with state oversight", "mil_exp": 3.7, "internet": 99.0, "cultural_alignment": "Middle East"},
    "NATO": {"gdp": 25.0, "influence": 0.97, "position": "Collective security & data interoperability", "mil_exp": 2.5, "internet": 90.0, "cultural_alignment": "Western Alliance"},
    "Greenland": {"gdp": 0.003, "influence": 0.45, "position": "Emerging Arctic tech governance", "mil_exp": 0.0, "internet": 68.0, "cultural_alignment": "Nordic"},
    "Venezuela": {"gdp": 0.048, "influence": 0.58, "position": "State-controlled digital infrastructure", "mil_exp": 0.9, "internet": 72.0, "cultural_alignment": "Latin American"}
}


# Load real-world data
if AGPO_AVAILABLE and not st.session_state["api_data_loaded"]:
    with st.spinner("🌍 Loading real-world data from APIs..."):
        for country, iso_code in country_to_iso.items():
            try:
                # Get World Bank data
                gdp = get_latest_gdp(iso_code)
                mil_exp = get_latest_military_expenditure(iso_code)
                internet = get_internet_penetration(iso_code)

                # Update default data with real values
                if gdp is not None:
                    try:
                        default_data[country]["gdp"] = round(float(gdp), 2)
                    except (ValueError, TypeError):
                        pass
                if mil_exp is not None:
                    try:
                        default_data[country]["mil_exp"] = round(float(mil_exp), 2)
                    except (ValueError, TypeError):
                        pass
                if internet is not None:
                    try:
                        default_data[country]["internet"] = round(float(internet), 1)
                    except (ValueError, TypeError):
                        pass

                # Integrate into adjudicator
                adjudicator.integrate_real_world_data(
                    iso_code,
                    gdp=default_data[country]["gdp"],
                    mil_exp=default_data[country]["mil_exp"],
                    internet=default_data[country]["internet"]
                )

            except Exception as e:
                st.warning(f"Could not load data for {country}: {e}")

        # Get sanctions data
        try:
            sanctions_df = fetch_consolidated_screening_list()
            if not sanctions_df.empty:
                sanctioned_countries = get_sanctioned_countries()
                for country, iso_code in country_to_iso.items():
                    country_name = country if country != "Dubai" else "United Arab Emirates"
                    sanction_count = sanctioned_countries.get(country_name, 0)
                    adjudicator.integrate_real_world_data(
                        iso_code,
                        sanctions=sanction_count
                    )
        except Exception as e:
            # Silently continue if export controls API fails
            pass

        st.session_state["api_data_loaded"] = True
        st.success("✅ Real-world data loaded successfully!")

selected_country_a = st.selectbox("Select Country A", country_options, index=0)
selected_country_b = st.selectbox("Select Country B", country_options, index=1)

role_tags = ["Governance","MilitaryAI","DataPrivacy","ExportControl","Diplomacy","StandardSetting","Surveillance","Trade","TechAlliance"]
role_country_a = st.selectbox(f"Role for {selected_country_a}", role_tags, key="role_a")
role_country_b = st.selectbox(f"Role for {selected_country_b}", role_tags, key="role_b")

player_country = st.selectbox("🎖️ You represent:", country_options, index=0)

# ==============================================================
# 🧭 Policy Owner (Narrative) — Manual or Agentic
# - Generates responses to objections + a concessions menu
# - Does NOT edit policy text (text amendments happen on the Policy Stress Testing Platform page)
# ==============================================================
import os, json, textwrap
import requests

def _openai_chat(messages, model="gpt-4o-mini", temperature=0.4, max_tokens=500):
    """Lightweight OpenAI Chat Completions via HTTPS. Works in Colab without extra deps.
    If OPENAI_API_KEY is missing, returns None.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("AURACELLE_OPENAI_MODEL", model),
                "messages": messages,
                "temperature": float(os.getenv("AURACELLE_OPENAI_TEMPERATURE", temperature)),
                "max_tokens": int(os.getenv("AURACELLE_OPENAI_MAX_TOKENS", max_tokens)),
            },
            timeout=30,
        )
        data = resp.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
    return None

def _heuristic_policy_owner_narrative(selected_policy, rep_country, objections, concessions, aggressiveness):
    """Fallback narrative when no API key is available."""
    conc = ", ".join(concessions) if concessions else "limited targeted concessions"
    obj = objections.strip() if objections.strip() else "No explicit objections provided yet."
    tone = {"Low":"measured, collaborative", "Medium":"firm but constructive", "High":"hard-nosed, stability-first"}.get(aggressiveness, "measured, collaborative")
    return textwrap.dedent(f"""
    **Policy Owner Narrative (heuristic)**
    - **Policy frame:** {selected_policy}
    - **You represent:** {rep_country}
    - **Tone:** {tone}

    **Acknowledgement**
    I hear the core concerns: {obj}

    **Response (what you say in the room)**
    Our objective is to preserve *legitimate national interests* while preventing predictable failure modes (compliance gaming, trust collapse, enforcement gaps, coalition fracture).
    We will not expand scope unnecessarily; we will focus on measurable risk thresholds and implementability.

    **Concessions we can offer (without rewriting the policy)**
    - {conc}
    - Sequencing: pilot → review gate → scale only if metrics improve
    - Confidential channels where disclosure could create security exposure

    **Non‑negotiables**
    - Minimum baseline assurance for high-risk frontier capabilities
    - Clear accountability for violations (graduated, not arbitrary)
    - Mutual transparency mechanisms sufficient to deter gaming

    **Ask back to counterparts**
    - What clause or mechanism would shift you from *hedge/oppose* to *support* while keeping the policy enforceable?
    """).strip()

def generate_policy_owner_narrative(selected_policy, rep_country, objections, concessions, aggressiveness):
    system = ("You are the Policy Owner in an AI governance wargaming workshop. "
              "You must respond to objections in a way that preserves policy intent, "
              "offers pragmatic concessions, and identifies non-negotiables. "
              "Do NOT rewrite the full policy text; provide negotiation posture and talking points only.")
    user = f"""Policy scenario: {selected_policy}
Representative country/actor: {rep_country}
Aggressiveness: {aggressiveness}

Objections (from country leads / stakeholders):
{objections}

Concessions menu (allowed levers):
{json.dumps(concessions, ensure_ascii=False)}

Produce:
1) 5–8 bullet talking points responding to objections
2) 3 pragmatic concessions (using the menu) + rationale
3) 3 non-negotiables
4) A one-paragraph 'closing statement' suitable for plenary.
"""
    out = _openai_chat(
        [{"role":"system","content":system},{"role":"user","content":user}],
        max_tokens=650
    )
    if out:
        return out
    return _heuristic_policy_owner_narrative(selected_policy, rep_country, objections, concessions, aggressiveness)

with st.expander("🧭 Policy Owner (Narrative) — respond to objections (no text edits)", expanded=False):
    st.caption("Use this on the Simulation page to generate negotiation posture and responses. Text amendments are handled on the Policy Stress Testing Platform page.")
    po_mode = st.radio("Policy Owner Mode", ["Manual", "Agentic AI"], horizontal=True, key="po_narrative_mode")
    aggressiveness = st.select_slider("Stance aggressiveness", options=["Low","Medium","High"], value="Medium", key="po_narrative_aggr")

    concessions_menu = [
        "Narrow scope to threshold models",
        "Mutual recognition audits (vs independent inspections)",
        "Safe harbor for incident reporting",
        "Confidential reporting channel",
        "Graduated enforcement ladder",
        "Capacity-building support package",
        "Pilot-first with review gate",
        "Regional implementation first",
        "Explicit national security carve-out (narrow)",
        "Private-sector compliance credits / incentives",
    ]
    selected_concessions = st.multiselect("Concessions menu (select what you're willing to offer)", concessions_menu, default=["Pilot-first with review gate"])

    objections_txt = st.text_area("Objections to address (paste notes from Country Leads)", height=140, key="po_narrative_objections")

    if po_mode == "Manual":
        st.info("Manual mode: type your own narrative response below and use it during rounds.")
        manual_resp = st.text_area("Your Policy Owner narrative response", height=180, key="po_narrative_manual_resp")
        if st.button("Save manual response", key="po_save_manual"):
            st.session_state["po_narrative_output"] = manual_resp.strip()
    else:
        if st.button("Generate narrative response (Agentic)", key="po_generate_narrative"):
            st.session_state["po_narrative_output"] = generate_policy_owner_narrative(
                selected_policy=selected_policy,
                rep_country=player_country,
                objections=objections_txt,
                concessions=selected_concessions,
                aggressiveness=aggressiveness
            )

    if st.session_state.get("po_narrative_output"):
        st.markdown("### Policy Owner Output")
        st.markdown(st.session_state["po_narrative_output"])

# --- Round header + Agent-style controls ---
round_col1, round_col2, round_col3 = st.columns([1, 1, 1])

with round_col1:
    st.subheader(f"🕐 Round: {st.session_state['round']}")

with round_col2:
    # Episode length controls how many rounds conceptually form one episode
    st.session_state["episode_length"] = st.slider(
        "Episode Length (rounds)",
        min_value=1,
        max_value=30,
        value=st.session_state.get("episode_length", 5),
        key="episode_length_slider"
    )

with round_col3:
    st.session_state["stochastic_exploration"] = st.toggle(
        "Enable Stochastic Exploration",
        value=st.session_state.get("stochastic_exploration", False),
        help="When enabled, the adjudication introduces variability into reward and risk.",
        key="stochastic_exploration_toggle"
    )

# --- Reward & Risk computation (lightweight, sim-style) ---
# alignment_score is set later during Policy Position Comparison; default safely here
alignment_score = float(st.session_state.get("alignment_score", 0.5))


# ---- Safe defaults for reward components (prevents NameError in early rounds)
adjudication = st.session_state.get("adjudication")
if not isinstance(adjudication, dict):
    adjudication = {
        "tension_index": 0.5,
        "confidence_score": 0.7,
        "status": "not evaluated",
        "notes": "Agentic adjudicator updates after inputs are provided."
    }
    st.session_state["adjudication"] = adjudication

base_reward = (alignment_score * 0.5
               + (1.0 - adjudication["tension_index"]) * 0.3
               + adjudication["confidence_score"] * 0.2)

if st.session_state.get("stochastic_exploration", False):
    exploration_noise = np.random.normal(0, 0.05)
    base_reward = max(0.0, min(1.0, base_reward + exploration_noise))

reward = float(base_reward)
risk = float(adjudication["tension_index"])

# Log round metrics for batch evaluation
st.session_state["round_metrics_trace"].append({
    "round": int(st.session_state["round"]),
    "reward": reward,
    "risk": risk,
    "tension": float(adjudication["tension_index"]),
    "confidence": float(adjudication["confidence_score"]),
    "alignment": float(alignment_score),
})

# --- Reward & Risk display ---
metric_col1, metric_col2, metric_col3 = st.columns(3)
with metric_col1:
    st.metric("🏆 Reward", f"{reward*100:.1f}")
with metric_col2:
    st.metric("⚠️ Risk", f"{risk*100:.1f}")
with metric_col3:
    # Episode progress within the chosen episode length
    ep_pos = (st.session_state["round"] - 1) % st.session_state["episode_length"] + 1
    st.metric("📏 Episode Progress", f"{ep_pos}/{st.session_state['episode_length']}")

# --- Round navigation controls ---
nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("▶️ Next Round"):
        log_move(session_id=st.session_state.get("session_id"), participant_id=st.session_state.get("participant_id"), round_num=st.session_state.get("round_num"), policy=st.session_state.get("policy_selected"), action="next_round", notes="", state={"reward": st.session_state.get("reward"), "risk": st.session_state.get("risk"), "tension": st.session_state.get("tension"), "alignment": st.session_state.get("alignment")})
        st.session_state["round"] += 1
        st.rerun()
with nav_col2:
    if st.button("🔄 Reset Episode"):
        st.session_state["round"] = 1
        st.session_state["round_metrics_trace"] = []
        st.rerun()



# Display real-world data comparison
st.subheader("🤖 AI Agentic Adjudicator Status")

actor_beliefs = {
    selected_country_a: default_data[selected_country_a]["position"],
    selected_country_b: default_data[selected_country_b]["position"]
}
power_levels = {
    selected_country_a: default_data[selected_country_a]["influence"],
    selected_country_b: default_data[selected_country_b]["influence"]
}
alignment_graph = {(selected_country_a, selected_country_b): alignment_score}

adjudication = adjudicator.adjudicate(actor_beliefs, power_levels, alignment_graph, st.session_state["round"])

col1, col2, col3, col4 = st.columns(4)
with col1:
    tension_color = "🔴" if adjudication["tension_index"] > 0.7 else ("🟡" if adjudication["tension_index"] > 0.4 else "🟢")
    st.metric(f"{tension_color} Tension", f"{adjudication['tension_index']*100:.1f}%")
with col2:
    st.metric("🎲 Confidence", f"{adjudication['confidence_score']*100:.1f}%")
with col3:
    st.metric("📊 Alignment", f"{alignment_score*100:.0f}%")
with col4:
    real_world_icon = "✅" if adjudication.get("real_world_integrated") else "⚠️"
    st.metric(f"{real_world_icon} Real Data", "Active" if adjudication.get("real_world_integrated") else "Simulated")

st.markdown("### 🎭 Deception Detection")
deception_df = pd.DataFrame([
    {"Actor": k, "Risk": f"{v*100:.1f}%", "Status": "⚠️ Suspicious" if v > 0.5 else "✅ Consistent"}
    for k, v in adjudication["deception_scores"].items()
])
st.dataframe(deception_df, use_container_width=True)

if adjudication["shock_event"]:
    shock_prefix = "💥 **REAL-WORLD TRIGGERED SHOCK**" if adjudication["shock_event"].get("real_world_triggered") else "💥 **EXTERNAL SHOCK**"
    st.warning(f"{shock_prefix}\\n\\n{adjudication['narrative']}")
    st.session_state["event_log"].append(adjudication["shock_event"])
else:
    st.info(f"ℹ️ {adjudication['narrative']}")

st.subheader("🆚 Policy Position Comparison (Real-World Data)")
comparison_df = pd.DataFrame({
    "Metric": ["GDP (Trillion USD)", "Military Exp (% GDP)", "Internet Penetration (%)", "Influence Score", "AI Policy Position"],
    selected_country_a: [
        f"${default_data[selected_country_a]['gdp']:.2f}T",
        f"{default_data[selected_country_a]['mil_exp']:.1f}%",
        f"{default_data[selected_country_a]['internet']:.1f}%",
        default_data[selected_country_a]["influence"],
        default_data[selected_country_a]["position"]
    ],
    selected_country_b: [
        f"${default_data[selected_country_b]['gdp']:.2f}T",
        f"{default_data[selected_country_b]['mil_exp']:.1f}%",
        f"{default_data[selected_country_b]['internet']:.1f}%",
        default_data[selected_country_b]["influence"],
        default_data[selected_country_b]["position"]
    ]
})
st.table(comparison_df)

player_new_position = st.text_input("📜 Propose New Policy Position", value=default_data[player_country]["position"])
opponent_country = selected_country_b if player_country == selected_country_a else selected_country_a
alignment_score = 1.0 if player_new_position == default_data[opponent_country]["position"] else 0.0


st.session_state["alignment_score"] = float(alignment_score)
st.markdown("---")


st.markdown("---")
# Strategic Analysis
st.markdown("---")
st.subheader("🎯 Strategic Analysis & Recommendations")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown(f"**{selected_country_a} Assessment**")

    # Economic power analysis
    gdp_a = default_data[selected_country_a]["gdp"]
    gdp_b = default_data[selected_country_b]["gdp"]
    gdp_ratio = gdp_a / (gdp_b + 0.01)

    if gdp_ratio > 2.0:
        st.success(f"✅ Strong economic advantage ({gdp_ratio:.1f}x GDP)")
    elif gdp_ratio < 0.5:
        st.warning(f"⚠️ Economic disadvantage ({gdp_ratio:.1f}x GDP)")
    else:
        st.info(f"📊 Comparable economic power ({gdp_ratio:.1f}x GDP)")

    # Military analysis
    mil_a = default_data[selected_country_a]["mil_exp"]
    if mil_a > 3.0:
        st.warning(f"⚠️ High military expenditure ({mil_a:.1f}% GDP) - potential aggression signal")
    elif mil_a < 1.5:
        st.info(f"🕊️ Low military expenditure ({mil_a:.1f}% GDP) - peaceful stance")
    else:
        st.success(f"✅ Moderate military spending ({mil_a:.1f}% GDP)")

    # Digital infrastructure
    internet_a = default_data[selected_country_a]["internet"]
    if internet_a > 90:
        st.success(f"✅ Advanced digital infrastructure ({internet_a:.0f}% penetration)")
    elif internet_a < 60:
        st.warning(f"⚠️ Limited digital infrastructure ({internet_a:.0f}% penetration)")
    else:
        st.info(f"📊 Developing digital infrastructure ({internet_a:.0f}% penetration)")

with col_right:
    st.markdown(f"**{selected_country_b} Assessment**")

    # Economic power analysis
    if gdp_ratio < 0.5:
        st.success(f"✅ Strong economic advantage ({1/gdp_ratio:.1f}x GDP)")
    elif gdp_ratio > 2.0:
        st.warning(f"⚠️ Economic disadvantage ({1/gdp_ratio:.1f}x GDP)")
    else:
        st.info(f"📊 Comparable economic power ({1/gdp_ratio:.1f}x GDP)")

    # Military analysis
    mil_b = default_data[selected_country_b]["mil_exp"]
    if mil_b > 3.0:
        st.warning(f"⚠️ High military expenditure ({mil_b:.1f}% GDP) - potential aggression signal")
    elif mil_b < 1.5:
        st.info(f"🕊️ Low military expenditure ({mil_b:.1f}% GDP) - peaceful stance")
    else:
        st.success(f"✅ Moderate military spending ({mil_b:.1f}% GDP)")

    # Digital infrastructure
    internet_b = default_data[selected_country_b]["internet"]
    if internet_b > 90:
        st.success(f"✅ Advanced digital infrastructure ({internet_b:.0f}% penetration)")
    elif internet_b < 60:
        st.warning(f"⚠️ Limited digital infrastructure ({internet_b:.0f}% penetration)")
    else:
        st.info(f"📊 Developing digital infrastructure ({internet_b:.0f}% penetration)")

# Adjudicator Recommendations
st.markdown("#### 🤖 Adjudicator Recommendations")

if adjudication["tension_index"] > 0.7:
    st.error("""
    **🔴 CRITICAL TENSION LEVEL**
    - Immediate de-escalation measures recommended
    - Consider confidence-building measures
    - Establish backchannel communications
    - Risk of shock events: HIGH
    """)
elif adjudication["tension_index"] > 0.4:
    st.warning("""
    **🟡 ELEVATED TENSION**
    - Monitor situation closely
    - Prepare contingency plans
    - Diplomatic engagement advised
    - Risk of shock events: MODERATE
    """)
else:
    st.success("""
    **🟢 LOW TENSION**
    - Favorable conditions for negotiation
    - Opportunity for comprehensive agreements
    - Continue current engagement strategy
    - Risk of shock events: LOW
    """)

# Export Functionality
st.markdown("---")
st.subheader("📥 Export Simulation Data")

col_export1, col_export2 = st.columns(2)

with col_export1:
    if st.button("📊 Export Full Report"):
        data_status = 'Active ✅' if adjudication.get('real_world_integrated') else 'Simulated ⚠️'

        report = f"""# Auracelle Charlie 3 - War Gaming Stress-Testing Policy Governance Research Simulation/Prototype - Simulation Report
## Generated: {adjudication.get('timestamp', 'N/A')}
### Round: {st.session_state['round']}

## Configuration
- **Policy Scenario:** {selected_policy}
- **Country A:** {selected_country_a} (Role: {role_country_a})
- **Country B:** {selected_country_b} (Role: {role_country_b})
- **Player:** {player_country}

## Real-World Data Integration
- **Data Sources:** World Bank API, US Export Controls API
- **Status:** {data_status}

## Country A: {selected_country_a}
- **GDP:** ${default_data[selected_country_a]['gdp']:.2f} Trillion
- **Military Expenditure:** {default_data[selected_country_a]['mil_exp']:.1f}% of GDP
- **Internet Penetration:** {default_data[selected_country_a]['internet']:.1f}%
- **Influence Score:** {default_data[selected_country_a]['influence']:.2f}
- **Policy Position:** {default_data[selected_country_a]['position']}

## Country B: {selected_country_b}
- **GDP:** ${default_data[selected_country_b]['gdp']:.2f} Trillion
- **Military Expenditure:** {default_data[selected_country_b]['mil_exp']:.1f}% of GDP
- **Internet Penetration:** {default_data[selected_country_b]['internet']:.1f}%
- **Influence Score:** {default_data[selected_country_b]['influence']:.2f}
- **Policy Position:** {default_data[selected_country_b]['position']}

## Adjudication Results
- **Geopolitical Tension:** {adjudication['tension_index']*100:.1f}%
- **Alignment Score:** {alignment_score*100:.0f}%
- **Adjudicator Confidence:** {adjudication['confidence_score']*100:.1f}%

## Deception Analysis
"""
        for actor, score in adjudication['deception_scores'].items():
            risk_pct = score * 100
            report += f"- **{actor}:** {risk_pct:.1f}% risk\\n"

        total_events = len(st.session_state['event_log'])
        report += f"""
## Latest Event
{adjudication['narrative']}

## Total Events: {total_events}
"""

        st.download_button(
            label="📄 Download Report (Markdown)",
            data=report,
            file_name=f"auracelle_report_round_{st.session_state['round']}.md",
            mime="text/markdown"
        )

with col_export2:
    if st.button("📋 Export Event Log"):
        if st.session_state["event_log"]:
            event_df = pd.DataFrame(st.session_state["event_log"])
            csv = event_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"auracelle_events_round_{st.session_state['round']}.csv",
                mime="text/csv"
            )
        else:
            st.info("No events to export yet")

st.markdown("---")
st.caption("🤖 Auracelle Charlie 3 - War Gaming Stress-Testing Policy Governance Research Simulation/Prototype - AI Agentic Adjudicator with Real-World Data Integration | Powered by World Bank, US Export Controls, and SIPRI")
