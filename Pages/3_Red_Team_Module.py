import streamlit as st

# --- Dropdown reference links (curated) ---
def _render_links(title, items):
    exp = st.expander(title, expanded=False)
    for label, url in items:
        exp.markdown(f"- [{label}]({url})")

_PROVENANCE = [
    ("World Bank Indicators API", "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation"),
    ("IMF World Economic Outlook Database", "https://www.imf.org/en/Publications/WEO/weo-database"),
    ("UN Comtrade+", "https://comtradeplus.un.org/"),
    ("SIPRI Databases", "https://www.sipri.org/databases"),
    ("WTO Tariff Analysis Online", "https://tao.wto.org/"),
]

_COGNITION_FIELDS = [
    ("Bounded rationality (Stanford Encyclopedia of Philosophy)", "https://plato.stanford.edu/entries/bounded-rationality/"),
    ("OODA loop (overview)", "https://en.wikipedia.org/wiki/OODA_loop"),
    ("Sensemaking (overview)", "https://en.wikipedia.org/wiki/Sensemaking"),
]

_BELIEF_FIELDS = [
    ("Bayesian inference (overview)", "https://en.wikipedia.org/wiki/Bayesian_inference"),
    ("Belief state (POMDP concept)", "https://en.wikipedia.org/wiki/Partially_observable_Markov_decision_process"),
]

_COGNITION_METRICS = [
    ("Calibration (statistics)", "https://en.wikipedia.org/wiki/Calibration_(statistics)"),
    ("Brier score", "https://en.wikipedia.org/wiki/Brier_score"),
    ("Entropy (information theory)", "https://en.wikipedia.org/wiki/Entropy_(information_theory)"),
]

import pandas as pd
import numpy as np
import json

st.set_page_config(page_title="Red Team Module", layout="wide")

st.title("🛡️ Red Team Module — Foresight Cognition & Belief Distortion")
st.caption("Stress-test how actors perceive, misperceive, and act on futures by attacking signals, framing, or cognition parameters.")

# -----------------------------
# Helpers
# -----------------------------
def clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def init_agents(names):
    agents = {}
    for n in names:
        agents[n] = {
            "cognition": {
                "H": 3,          # Horizon depth (1..K)
                "Omega": 0.55,   # Openness/update rate (0..1)
                "Lambda": 0.55,  # Uncertainty tolerance (0..1)
                "Pi": 0.45       # Narrative lock-in (0..1)
            },
            "belief": {
                "mu": 0.50,      # Expected outcome proxy (0..1)
                "sigma": 0.25    # Uncertainty proxy (0..1)
            },
            "metrics": {
                "USI": None,     # Update suppression index
                "HD": 0          # Horizon degradation
            }
        }
    return agents

def compute_alpha(cog):
    # alpha = Omega * (1 - Pi)
    return clip01(cog["Omega"] * (1.0 - cog["Pi"]))

def update_belief(agent, evidence):
    """
    Cognition-weighted belief update (lightweight, explainable).
    evidence: float in [-1, 1] where + pushes mu upward, - downward
    """
    cog = agent["cognition"]
    bel = agent["belief"]

    alpha = compute_alpha(cog)

    # Map evidence to [0,1] target for mu
    target = clip01(0.5 + 0.5 * float(evidence))

    bel["mu"] = clip01((1 - alpha) * bel["mu"] + alpha * target)

    # Uncertainty update: low Lambda collapses uncertainty faster; high Lambda stays more agnostic
    collapse = (1.0 - cog["Lambda"]) * 0.20
    bel["sigma"] = clip01(bel["sigma"] * (1.0 - collapse))

    # Metrics
    agent["metrics"]["USI"] = clip01(1.0 - alpha)

def apply_red_team_move(agent, move, intensity, K=5):
    cog = agent["cognition"]
    bel = agent["belief"]

    if move == "Horizon Collapse":
        old = cog["H"]
        cog["H"] = int(max(1, cog["H"] - int(round(intensity * 2))))
        agent["metrics"]["HD"] += (old - cog["H"])

    elif move == "Narrative Entrenchment":
        cog["Pi"] = clip01(cog["Pi"] + 0.35 * intensity)

    elif move == "Epistemic Distrust":
        cog["Omega"] = clip01(cog["Omega"] - 0.35 * intensity)

    elif move == "Panic Amplification":
        cog["Lambda"] = clip01(cog["Lambda"] - 0.35 * intensity)

    elif move == "Metric Spoofing":
        # Push mu in a misleading direction without improving the agent's cognition (signal tampering)
        bel["mu"] = clip01(bel["mu"] + (0.25 * intensity))

    elif move == "Frame Flip":
        # Invert the meaning of recent evidence by effectively flipping openness for one step
        cog["Omega"] = clip01(1.0 - cog["Omega"])

    else:
        pass

# -----------------------------
# State bootstrap
# -----------------------------
# Try to reuse existing Simulation state if present; otherwise initialize safely
if "charlie_agents" not in st.session_state:
    # Prefer any actor list from Simulation (if you stored it), else default to your Charlie set
    default_actors = st.session_state.get("actor_list") or [
        "Dubai", "UK", "US", "Japan", "China", "Brazil", "India", "NATO",
        "Israel", "Paraguay", "Belgium", "Denmark", "Ukraine", "Serbia",
        "Argentina", "Norway", "Switzerland", "Poland", "Global South"
    ]
    st.session_state["charlie_agents"] = init_agents(default_actors)

agents = st.session_state["charlie_agents"]
actor_names = list(agents.keys())

# -----------------------------
# Sidebar controls (clickable module config)
# -----------------------------
st.sidebar.header("Red Team Controls")
target = st.sidebar.selectbox("Target actor", actor_names, index=0)
move = st.sidebar.selectbox(
    "Belief-distortion move",
    [
        "Narrative Entrenchment",
        "Epistemic Distrust",
        "Horizon Collapse",
        "Panic Amplification",
        "Metric Spoofing",
        "Frame Flip",
    ],
    index=0
)
intensity = st.sidebar.slider("Intensity", 0.0, 1.0, 0.5, 0.05)

evidence = st.sidebar.slider("New evidence signal (for belief update)", -1.0, 1.0, 0.2, 0.05)
apply_move = st.sidebar.button("Apply Red Team Move", use_container_width=True)
apply_update = st.sidebar.button("Run Cognition-Weighted Belief Update", use_container_width=True)
reset = st.sidebar.button("Reset module state", use_container_width=True)

if reset:
    st.session_state["charlie_agents"] = init_agents(actor_names)
    agents = st.session_state["charlie_agents"]
    st.success("Reset Red Team module state.")

# -----------------------------
# Execute actions
# -----------------------------
if apply_move:
    apply_red_team_move(agents[target], move, intensity)
    st.success(f"Applied **{move}** to **{target}** (intensity={intensity:.2f}).")

if apply_update:
    update_belief(agents[target], evidence)
    st.success(f"Updated beliefs for **{target}** using evidence={evidence:.2f}.")

# -----------------------------
# Display
# -----------------------------
st.markdown(
    """
<style>
/* reduce top padding and tighten layout a bit */
section.main > div { padding-top: 1rem; }
/* tighten spacing above the dataframe */
div[data-testid="stDataFrame"] { margin-top: 0.25rem; }
</style>
""",
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Target actor — cognition & belief")
    st.write(f"**Actor:** {target}")

    cog = agents[target]["cognition"]
    bel = agents[target]["belief"]
    met = agents[target]["metrics"]

    st.markdown("**Cognition state (C) — real-world fields**")
    st.markdown("""
- **H** (Planning Horizon): how many turns ahead the actor considers
- **Omega** (Update Openness): willingness to revise beliefs when new evidence arrives
- **Lambda** (Uncertainty Tolerance): comfort operating under ambiguity and incomplete information
- **Pi** (Narrative Commitment): how strongly the actor is locked into a doctrine/storyline
""")
    st.code(json.dumps(cog, indent=2), language="json")

    st.markdown("**Belief state (b) — real-world fields**")
    st.markdown("""
- **mu** (Expected Outcome Score): 0.0 to 1.0 proxy for how well things are going
- **sigma** (Uncertainty Level): 0.0 to 1.0 proxy for how unsure the actor is
""")
    st.code(json.dumps(bel, indent=2), language="json")

    st.markdown("**Cognition metrics**")
    st.markdown("""
- **USI** (Update Suppression Index): higher means less learning / more "stuck"
- **HD** (Horizon Degradation): how much the planning horizon has been reduced by attacks
""")
    st.code(json.dumps(met, indent=2), language="json")

with col2:
    st.subheader("Data & evidence provenance (what feeds the sandbox)")
    st.info(
        "Auracelle Charlie is designed to be data-driven and evidence-based. "
        "This Red Team module manipulates cognition variables, but it is intended to sit on top of the "
        "real-world data streams used in the Simulation page."
    )

    st.markdown("**Current data resources (in this baseline):**")
    st.markdown("""
- **World Bank (wbgapi)**: macro indicators (GDP, population, etc.) pulled via API
- **U.S. Consolidated Screening List (CSL)**: export-control / sanctions screening via API wrapper
- **SIPRI**: military expenditure reference data (CSV upload)

For assurance, add an Evidence Ledger export that records each metric with dataset name, vintage/date, access method, and transformation.
""")

    st.markdown("**Recommended NATO-grade traceability upgrades:**")
    st.markdown("""
- Attach a **Source** tag to every metric (dataset name, vintage/date, access method)
- Attach a **Transformation** tag (how the raw data is normalized/scored)
- Provide an **Export** button for an **Evidence Ledger** (metric → source → transformation → timestamp/round)
""")

st.subheader("All actors — cognition & belief table")
rows = []
for name, a in agents.items():
    c = a["cognition"]
    b = a["belief"]
    m = a["metrics"]
    alpha = compute_alpha(c)
    rows.append({
        "Actor": name,
        "Planning horizon (H)": c["H"],
        "Evidence update openness (Omega)": round(c["Omega"], 3),
        "Uncertainty tolerance (Lambda)": round(c["Lambda"], 3),
        "Narrative lock-in (Pi)": round(c["Pi"], 3),
        "Learning rate (alpha)": round(alpha, 3),
        "Expected outcome (mu)": round(b["mu"], 3),
        "Uncertainty (sigma)": round(b["sigma"], 3),
        "Update suppression (USI)": None if m["USI"] is None else round(m["USI"], 3),
        "Horizon degradation (HD)": m["HD"],
    })
df = pd.DataFrame(rows).sort_values("Actor")
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.markdown(
    """
**How to use this module**
- Use **Apply Red Team Move** to distort cognition (H, Omega, Lambda, Pi) or distort signals (Metric Spoofing / Frame Flip).
- Use **Run Cognition-Weighted Belief Update** to see how the target updates beliefs under its current cognition state.
- The key diagnostic is **USI (Update Suppression Index)**: higher = more “stuck” / less learning.
"""
)

st.markdown("## References (dropdown links)")
_render_links("Data & evidence provenance (what feeds the sandbox)", _PROVENANCE)
_render_links("Cognition state (C) — real-world fields", _COGNITION_FIELDS)
_render_links("Belief state (b) — real-world fields", _BELIEF_FIELDS)
_render_links("Cognition metrics", _COGNITION_METRICS)
