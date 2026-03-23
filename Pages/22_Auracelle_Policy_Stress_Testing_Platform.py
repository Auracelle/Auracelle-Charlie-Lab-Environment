import streamlit as st
import numpy as np
import re
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import date

from api_client import post_metrics
from agpo_rl_engine import EAGPOEnv, QAgent, ACTION_NAMES, COOPERATE, TIGHTEN, DEFECT, institutional_capacity_from_wb


# ------------------------------
# Agentic helpers (Policy Owner + Red Team)
# - Uses OpenAI if OPENAI_API_KEY is set; otherwise falls back to safe heuristics.
# - Patch-bounded: suggestions are append-only "Amendments" with max words.
# ------------------------------
import os, json, textwrap
from typing import Dict, Any, List, Optional

def _try_openai_chat(system: str, user: str, temperature: float = 0.3) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.environ.get("AURACELLE_OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=float(temperature),
            messages=[
                {"role":"system","content":system},
                {"role":"user","content":user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None

def _word_limit(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return (text or "").strip()
    return " ".join(words[:max_words]).strip() + " …"

def red_team_agent(policy_text: str, actors: List[str], round_no: int, aggressiveness: str) -> Dict[str, Any]:
    """Return an inject + predicted failure mode, workshop-safe (no operational wrongdoing)."""
    agg = aggressiveness.lower()
    system = (
        "You are the Red Team for a policy stress-testing workshop. "
        "Your job is to propose governance failure-mode scenarios and counterfactuals. "
        "You must stay at the policy/governance level (no technical exploitation instructions). "
        "Output must be concise and structured as JSON with keys: inject_title, inject, failure_mode, why_it_breaks, suggested_controls."
    )
    user = f"""Round {round_no}. Actors: {actors}.
Aggressiveness: {aggressiveness}.
Policy draft:
{policy_text}

Propose 1 inject scenario (governance-level) and 1 predicted failure mode.
Return JSON only."""
    out = _try_openai_chat(system, user, temperature=0.4 if agg=="high" else 0.25)
    if out:
        try:
            data = json.loads(out)
            return data if isinstance(data, dict) else {"inject_title":"Red Team Inject","inject":out,"failure_mode":"Unknown","why_it_breaks":"","suggested_controls":""}
        except Exception:
            return {"inject_title":"Red Team Inject","inject":out,"failure_mode":"Governance fragility","why_it_breaks":"","suggested_controls":""}

    # Heuristic fallback
    library = {
        "low": ("Ambiguity & compliance drift", "Compliance gaming", "Definitions are vague; actors interpret differently.", "Add measurable thresholds; clear audit trail; tiered compliance."),
        "medium": ("Coalition fracture under enforcement", "Coalition fracture", "Enforcement is uneven; allies disagree; non-aligned hedge.", "Graduated enforcement; mutual recognition; capacity support."),
        "high": ("Retaliation + forum shopping spiral", "Trust collapse", "Actors retaliate; firms relocate; reporting gets politicized.", "Safe harbor reporting; confidentiality; independent escalation channel."),
    }
    title, mode, why, controls = library.get(agg, library["medium"])
    return {
        "inject_title": title,
        "inject": f"Introduce a stress event aligned with '{title}' that pressures reporting/enforcement and triggers hedging among {actors}.",
        "failure_mode": mode,
        "why_it_breaks": why,
        "suggested_controls": controls,
    }

def policy_owner_agent(policy_text: str, round_summary: str, metrics: Dict[str, Any], max_edits: int, max_words: int) -> Dict[str, Any]:
    """Return 1–3 targeted append-only amendments (bounded)."""
    system = (
        "You are the Policy Owner in a policy stress-testing workshop. "
        "You must preserve intent and propose small, specific amendments (append-only) to improve durability and reduce vulnerabilities. "
        "Do not rewrite the whole policy. "
        "Output must be concise JSON with keys: intent_preserved, amendments (list of strings), rationale."
    )
    user = f"""Policy draft:
{policy_text}

Round summary (opposition/hedging/breakpoints):
{round_summary}

Observed metrics:
{json.dumps(metrics, indent=2)}

Constraints:
- Propose up to {max_edits} amendments.
- Total amendment text must be under {max_words} words (append-only).

Return JSON only."""
    out = _try_openai_chat(system, user, temperature=0.25)
    if out:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and "amendments" in data:
                # enforce word limit defensively
                ams = data.get("amendments", [])
                if isinstance(ams, list):
                    joined = "\n".join([str(a).strip() for a in ams if str(a).strip()])
                    joined = _word_limit(joined, int(max_words))
                    data["amendments"] = [a.strip() for a in joined.split("\n") if a.strip()][:int(max_edits)]
                return data
        except Exception:
            pass

    # Heuristic fallback (bounded)
    candidates = [
        "Amendment: Define scope thresholds for 'frontier' systems (capability + deployment context) and explicitly exclude low-risk systems.",
        "Amendment: Replace single-step penalties with graduated enforcement (notice → remediation window → proportional measures).",
        "Amendment: Add confidential incident reporting safe-harbor and a non-attribution technical review channel.",
        "Amendment: Add mutual recognition of audits and minimum evidence requirements (assurance case + eval summary + change log).",
        "Amendment: Add capacity-building support and implementation timelines for lower-capacity stakeholders.",
    ]
    ams = candidates[:max(1, min(int(max_edits), 3))]
    joined = _word_limit("\n".join(ams), int(max_words))
    ams = [a.strip() for a in joined.split("\n") if a.strip()][:int(max_edits)]
    return {"intent_preserved": True, "amendments": ams, "rationale": "Targeted clarifications and enforcement safeguards to reduce hedging and improve durability."}

# ------------------------------
# Page config + minimal styling (Streamlit-native widgets; CSS only for look-and-feel)
# ------------------------------
st.set_page_config(layout="wide", page_title="Auracelle Policy Stress Testing Platform")

# Gate: require login/session setup
auth_ok = any(bool(st.session_state.get(k, False)) for k in ("authenticated","logged_in","is_authenticated","setup_complete","consent"))
if not auth_ok:
    st.warning("Please complete Session Setup / Login before using the Policy Stress Testing Platform.")
    st.stop()

st.markdown(
    """
    <style>
      .block-container {padding-top: 0.8rem; padding-bottom: 0.8rem;}
      [data-testid="stHeader"]{background: rgba(0,0,0,0);}
      [data-testid="stToolbar"]{right: 1.2rem;}
      .ac-topbar{
        border: 1px solid rgba(45,55,72,0.9);
        border-radius: 16px;
        padding: 14px 16px;
        background: linear-gradient(180deg, rgba(30,37,48,0.95) 0%, rgba(22,27,36,0.85) 100%);
        box-shadow: 0 10px 30px rgba(0,0,0,0.45);
        margin-bottom: 10px;
      }
      .ac-pill{
        display:inline-flex; align-items:center; gap:8px;
        padding: 6px 10px; border-radius: 999px;
        border: 1px solid rgba(16,185,129,0.9);
        background: rgba(16,185,129,0.12);
        font-size: 0.85rem;
      }
      .ac-title{
        font-weight: 700; letter-spacing: 0.06em; color: #00d4ff;
        margin: 0; line-height: 1.1;
      }
      .ac-subtitle{margin:0; color:#9ca3af; font-size:0.88rem;}
      .ac-card{
        border: 1px solid rgba(55,65,81,0.9);
        border-radius: 14px;
        padding: 14px;
        background: rgba(15,20,25,0.55);
        box-shadow: 0 8px 22px rgba(0,0,0,0.35);
      }
      .ac-muted{color:#9ca3af;}
      .ac-badge{
        display:inline-block; padding:6px 10px; border-radius: 10px;
        border:1px solid rgba(0,212,255,0.85);
        background: rgba(0,212,255,0.10);
        color:#00d4ff; font-weight:700; font-size:0.8rem;
      }
      .ac-badge-testing{
        border-color: rgba(245,158,11,0.9);
        background: rgba(245,158,11,0.12);
        color: #f59e0b;
      }
      .ac-badge-pass{
        border-color: rgba(16,185,129,0.9);
        background: rgba(16,185,129,0.12);
        color:#10b981;
      }
      .ac-badge-fail{
        border-color: rgba(239,68,68,0.9);
        background: rgba(239,68,68,0.12);
        color:#ef4444;
      }
      .ac-kpi{
        display:flex; gap:18px; flex-wrap:wrap; margin-top:8px;
      }
      .ac-kpi-item{
        padding:10px 12px; border-radius: 12px;
        border:1px solid rgba(27,42,82,0.95);
        background: rgba(12,19,39,0.55);
        min-width: 150px;
      }
      .ac-kpi-v{font-size:1.15rem; font-weight:800;}
      .ac-kpi-l{font-size:0.8rem; color:#9AB0D6;}
      .ac-scenario-title{font-weight:800; font-size:1.05rem;}
      .ac-scenario-desc{color:#9ca3af; font-size:0.85rem; line-height:1.35;}
      .ac-bottombar{
        border: 1px solid rgba(45,55,72,0.9);
        border-radius: 16px;
        padding: 10px 12px;
        background: linear-gradient(180deg, rgba(30,37,48,0.70) 0%, rgba(22,27,36,0.55) 100%);
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        margin-top: 10px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------
# State
# ------------------------------
if "pst_results" not in st.session_state:
    st.session_state.pst_results = {}  # scenario_id -> dict
if "pst_selected" not in st.session_state:
    st.session_state.pst_selected = "coalition_stability"

ACTORS = ["US", "China", "India", "UK", "Japan", "Brazil", "Dubai", "NATO"]

# Actor-specific weights (interpretable defaults; can be tuned in E-AGPO-HT docs)
DEFAULT_RISK_WEIGHT = {
    "US": 0.62, "China": 0.55, "India": 0.58, "UK": 0.64,
    "Japan": 0.66, "Brazil": 0.54, "Dubai": 0.60, "NATO": 0.63,
}
DEFAULT_SANCTION_SENS = {
    "US": 0.18, "China": 0.30, "India": 0.22, "UK": 0.20,
    "Japan": 0.21, "Brazil": 0.24, "Dubai": 0.20, "NATO": 0.19,
}
DEFAULT_CENTRALITY = {
    "US": 0.92, "China": 0.88, "India": 0.74, "UK": 0.70,
    "Japan": 0.68, "Brazil": 0.62, "Dubai": 0.55, "NATO": 0.80,
}

def _safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def fetch_actor_snapshot(actor, start_year, end_year, trade_year, policy_name, shock, intensity):
    """Live API snapshot from FastAPI /v2/metrics (World Bank/IMF/etc)."""
    return post_metrics(
        actor=actor,
        start_year=start_year,
        end_year=end_year,
        trade_year=trade_year,
        policy_name=policy_name,
        shock=shock,
        intensity=intensity,
    )

def build_actor_profiles(stakeholders, api_snapshots):
    profiles = {}
    for a in stakeholders:
        snap = api_snapshots.get(a, {}) if isinstance(api_snapshots, dict) else {}
        inst = institutional_capacity_from_wb(_safe_get(snap, "derived", "institutional_capacity", default=None), fallback=0.55)
        profiles[a] = {
            "risk_weight": float(DEFAULT_RISK_WEIGHT.get(a, 0.58)),
            "sanction_sensitivity": float(DEFAULT_SANCTION_SENS.get(a, 0.22)),
            "institutional_capacity": float(inst),
            "centrality": float(DEFAULT_CENTRALITY.get(a, 0.65)),
        }
    return profiles

def run_interpretable_marl(actor_profiles, episodes=80, epsilon=0.18, shock_sigma=0.03):
    """Multi-agent tabular Q-learning (interpretable) over the EAGPOEnv."""
    agents = {a: QAgent(a, epsilon=epsilon) for a in actor_profiles.keys()}

    durability_by_ep = []
    last_hist = None
    last_rewards = None

    for _ in range(int(episodes)):
        env = EAGPOEnv(actor_profiles)
        state = env.state()
        done = False
        while not done:
            actions = {a: agents[a].choose(state) for a in agents}
            next_state, rewards, done = env.step(actions, shock_sigma=float(shock_sigma))
            for a in agents:
                agents[a].update(state, actions[a], rewards[a], next_state)
            state = next_state
        durability_by_ep.append(env.durability())
        last_hist = env.history[:]  # (tension, stability, sanction_pressure, durability)
        last_rewards = rewards

    return {
        "durability_by_ep": np.array(durability_by_ep, dtype=float),
        "history": np.array(last_hist, dtype=float) if last_hist else np.zeros((0,4)),
        "last_rewards": last_rewards or {},
    }

def score_win_win(last_rewards):
    if not last_rewards:
        return 0.0
    vals = np.array(list(last_rewards.values()), dtype=float)
    # simple interpretable score: mean - std, rescaled to 0..100
    raw = float(np.mean(vals) - 0.50*np.std(vals))
    return float(np.clip(50 + 50*raw, 0, 100))

def count_vulnerabilities(history):
    if history.size == 0:
        return 0
    tension = history[-1, 0]
    sanc = history[-1, 2]
    vul = 0
    if tension > 0.70:
        vul += 2
    if sanc > 0.35:
        vul += 2
    if history[-1, 3] < 0.45:
        vul += 2
    return int(vul)

SCENARIOS = [
    {
        "id": "coalition_stability",
        "title": "Coalition Stability",
        "icon": "🤝",
        "desc": "Tests if agreements hold under asymmetric incentives and uneven capacity (coalition drift).",
        "shock_sigma": 0.03,
    },
    {
        "id": "free_rider_detection",
        "title": "Free Rider Detection",
        "icon": "🎭",
        "desc": "Identifies stakeholders who benefit without contributing (enforcement gaps).",
        "shock_sigma": 0.035,
    },
    {
        "id": "sanction_escalation",
        "title": "Sanction Escalation",
        "icon": "⚡",
        "desc": "Stress tests network-weighted sanction propagation and second-order effects.",
        "shock_sigma": 0.04,
    },
    {
        "id": "shock_resilience",
        "title": "Shock Resilience",
        "icon": "🌪️",
        "desc": "Injects stochastic shocks to evaluate recovery dynamics and durability under volatility.",
        "shock_sigma": 0.06,
    },
]

# ------------------------------
# TOP BAR (matches mock header concepts)
# ------------------------------
with st.container():
    c1, c2 = st.columns([2.2, 1.2])
    with c1:
        st.markdown(
            """
            <div class="ac-topbar">
              <div style="display:flex; align-items:center; gap:14px;">
                <div style="font-size:1.9rem;">🧬</div>
                <div>
                  <div class="ac-title">AURACELLE CHARLIE</div>
                  <div class="ac-subtitle">Policy Stress Testing &amp; Win-Win Optimization Platform</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown('<div class="ac-topbar" style="display:flex; align-items:center; justify-content:space-between; gap:10px;">', unsafe_allow_html=True)
        tech = st.selectbox("Technology Domain", ["🤖 AI Governance", "🧬 BioTech", "⚛️ Nuclear", "🛰️ Space", "🧪 Quantum"], index=0, label_visibility="collapsed")
        st.markdown('<span class="ac-pill"><span style="width:8px;height:8px;border-radius:999px;background:#10b981;display:inline-block;"></span>STRESS TEST READY</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------
# MAIN WORKSPACE: Left config | Center tests | Right analysis
# ------------------------------
left, mid, right = st.columns([1.15, 2.2, 1.15], gap="medium")

with left:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Policy Input")
    uploaded = st.file_uploader("Upload Policy Draft (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    policy_title = st.text_input("Policy Title", value="International AI Safety Standards")
    policy_summary = st.text_area(
        "Policy Summary / Draft",
        height=140,
        value="A cooperative verification and assurance framework for frontier AI systems, including disclosure, audits, incident response, and enforcement incentives."
    )

    st.divider()
    st.markdown("### 🤝 Stakeholders")
    stakeholders = st.multiselect("Select stakeholders", ACTORS, default=["US", "China", "India"])
    st.caption("Tip: keep this to 3-5 actors to maintain interpretability and speed.")

    st.divider()
    st.markdown("### ⚙️ Test Parameters")
    start_year, end_year = st.slider("Metrics window", min_value=2000, max_value=2024, value=(2000, 2024), step=1)
    trade_year = st.slider("Trade year", min_value=2010, max_value=2024, value=2024, step=1)
    intensity = st.slider("Policy intensity", min_value=0, max_value=100, value=62, step=1)
    shock = st.selectbox("Baseline shock", ["None", "SupplyChain", "CyberIncident", "BioEvent", "ConflictEscalation"], index=0)

    st.divider()
    st.markdown("### 🧠 Training")
    episodes = st.slider("Episodes", min_value=20, max_value=500, value=120, step=10)
    epsilon = st.slider("Exploration epsilon", min_value=0.00, max_value=0.50, value=0.18, step=0.01)
    base_sigma = st.slider("Shock volatility (sigma)", min_value=0.00, max_value=0.10, value=0.03, step=0.005)

    st.markdown('</div>', unsafe_allow_html=True)

with mid:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    # Banner
    badge = "TESTING" if st.session_state.pst_results else "READY"
    badge_class = "ac-badge-testing" if badge == "TESTING" else ""
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
          <div>
            <div style="font-size:1.45rem; font-weight:800;">{policy_title}</div>
            <div class="ac-muted" style="margin-top:4px;">
              🌐 Technology: <strong>{tech.replace("🤖 ","").replace("🧬 ","").replace("⚛️ ","").replace("🛰️ ","").replace("🧪 ","")}</strong>
              &nbsp;&nbsp;🤝 Stakeholders: <strong>{len(stakeholders)} Selected</strong>
              &nbsp;&nbsp;📅 Test Date: <strong>{date.today().isoformat()}</strong>
            </div>
          </div>
          <div class="ac-badge {badge_class}">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Robustness Tests", "Unintended Consequences", "Win-Win Analysis", "Implementation Stress", "Document Stress Test"])

    def scenario_status(sid):
        r = st.session_state.pst_results.get(sid)
        if not r:
            return ("READY", "ac-badge")
        if r.get("status") == "passed":
            return ("PASSED", "ac-badge ac-badge-pass")
        if r.get("status") == "failed":
            return ("FAILED", "ac-badge ac-badge-fail")
        return ("RUNNING", "ac-badge ac-badge-testing")

    def render_scenario_grid():
        cols = st.columns(2, gap="medium")
        for idx, sc in enumerate(SCENARIOS):
            sid = sc["id"]
            col = cols[idx % 2]
            with col:
                lab, klass = scenario_status(sid)
                r = st.session_state.pst_results.get(sid, {})
                win = float(r.get("win_win_score", 0.0))
                vul = int(r.get("vulnerabilities", 0))
                rounds = int(r.get("rounds", 0))
                stab = float(r.get("stability", 0.0))
                st.markdown('<div class="ac-card">', unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
                      <div class="ac-scenario-title">{sc["title"]}</div>
                      <div style="font-size:1.2rem;">{sc["icon"]}</div>
                    </div>
                    <div class="ac-scenario-desc" style="margin-top:6px;">{sc["desc"]}</div>
                    <div style="margin-top:10px;"><span class="{klass}">{lab}</span></div>
                    """,
                    unsafe_allow_html=True,
                )
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Win-Win", f"{win:.0f}%")
                kpi2.metric("Vuln", f"{vul}")
                kpi3.metric("Rounds", f"{rounds}")
                kpi4.metric("Stability", f"{stab:.0f}%")
                run = st.button("View / Run", key=f"run_{sid}", use_container_width=True)
                if run:
                    st.session_state.pst_selected = sid
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with tabs[0]:
            st.caption("Click a scenario to run it using your live API features + E-AGPO-HT-aligned interpretable MARL.")
            render_scenario_grid()

        with tabs[1]:
            st.markdown("#### Unintended consequences checklist")
            st.markdown(
                """
    - Second-order effects (trade diversion, monitoring burden, legitimacy loss)
    - Adversarial adaptation / regulatory arbitrage
    - Uneven compliance costs across stakeholders
    - Measurement gaming / audit shopping
                """
            )

        with tabs[2]:
            st.markdown("#### Win-win analysis")
            st.markdown(
                """
    Use the **Win-Win Optimization Score** and **Treaty Durability** as the two headline outcome measures.

    Suggested exploration:
    - Increase **policy intensity** until durability improves, but watch for stability drops.
    - Add a baseline **shock** (e.g., CyberIncident) and see whether outcomes remain Pareto-like.
    - Tune **volatility (sigma)** to test fragility vs. robustness.
                """
            )

        with tabs[3]:
            st.markdown("#### Implementation stress")
            st.markdown(
                """
    Implementation often fails at the seams. Stress test:
    - Capacity constraints (lowest-capacity actor)
    - Verification bandwidth (audit + reporting load)
    - Enforcement credibility under shocks
    - Cross-border evidence portability (what counts as "proof" across jurisdictions)
                """
            )

        with tabs[4]:
            st.markdown("#### Document stress test")
            st.caption("Upload a policy draft (or reuse the left-panel upload) to sanity-check decision density, stakeholder complexity, and ambiguity markers.")

            def _extract_text(uploaded_file):
                if uploaded_file is None:
                    return ""
                ext = uploaded_file.name.split(".")[-1].lower()
                if ext == "txt":
                    try:
                        return uploaded_file.read().decode("utf-8")
                    except Exception:
                        return uploaded_file.read().decode("utf-8", errors="ignore")
                if ext == "pdf":
                    try:
                        import PyPDF2
                        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                        return "\\n".join([(p.extract_text() or "") for p in reader.pages])
                    except Exception:
                        st.warning("PDF parsing requires PyPDF2 (install via pip).")
                        return ""
                if ext == "docx":
                    try:
                        import docx
                        doc = docx.Document(BytesIO(uploaded_file.read()))
                        return "\\n".join([p.text for p in doc.paragraphs])
                    except Exception:
                        st.warning("DOCX parsing requires python-docx (install via pip).")
                        return ""
                return ""

            doc_file = st.file_uploader("Policy draft (PDF/DOCX/TXT)", type=["pdf","docx","txt"], key="pst_doc_upload")
            if doc_file is None and uploaded is not None:
                doc_file = uploaded

            txt = _extract_text(doc_file) if doc_file is not None else ""
            if not txt.strip():
                st.info("Upload a document (or use the left-panel upload) to run a document stress test.")
            else:
                words = len(txt.split())
                sentences = max(1, len(re.findall(r"[.!?]+", txt)))
                decision_terms = ["shall","must","should","required","requires","approve","review","assess","audit","verify","ensure"]
                stakeholder_terms = ["board","committee","team","authority","regulator","audit","legal","oversight","operator","vendor","civil society"]
                ambiguity_terms = ["as appropriate","where feasible","when possible","reasonable","timely","adequate","sufficient","material","significant"]

                decision_hits = sum(txt.lower().count(t) for t in decision_terms)
                stakeholder_hits = sum(txt.lower().count(t) for t in stakeholder_terms)
                ambiguity_hits = sum(txt.lower().count(t) for t in ambiguity_terms)

                dpk = (decision_hits / max(1, words)) * 1000.0
                spk = (stakeholder_hits / max(1, words)) * 1000.0
                apk = (ambiguity_hits / max(1, words)) * 1000.0

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Words", f"{words:,}")
                c2.metric("Decision terms / 1k words", f"{dpk:.1f}")
                c3.metric("Stakeholder refs / 1k words", f"{spk:.1f}")
                c4.metric("Ambiguity markers / 1k words", f"{apk:.1f}")

                st.markdown("**Stress flags**")
                flags = []
                if dpk > 18:
                    flags.append("- High decision density: consider a decision log (owner, trigger, evidence, cadence).")
                if spk > 10:
                    flags.append("- Many stakeholders referenced: add an explicit RACI / accountability table.")
                if apk > 4:
                    flags.append("- Ambiguity markers detected: tighten definitions and measurable criteria.")
                if "incident" not in txt.lower():
                    flags.append("- Incident handling not obvious: add reporting + escalation triggers.")
                if not any(k in txt.lower() for k in ["audit","assurance","evaluation","test"]):
                    flags.append("- Assurance language not obvious: specify what evidence is produced and by whom.")
                if not flags:
                    flags.append("- No obvious red flags at this surface-level scan. Next: test enforcement incentives under shocks.")

                st.markdown("\\n".join(flags))

    st.divider()


    # ------------------------------

    # ------------------------------
    # 🎭 Working Group Modes (manual/agentic)
    # ------------------------------
    st.markdown("### 🎭 Working Group Modes")
    wg_mode = st.toggle("Enable Round-Based Workshop Mode", value=False, help="Step through rounds with manual/agentic Red Team and manual/agentic Policy Owner amendments.")
    st.markdown("**Policy Owner Mode**")
    policy_owner_mode = st.radio("Policy Owner Mode", ["Manual", "Agentic AI"], index=1, horizontal=True, label_visibility="collapsed")
    st.markdown("**Red Team Mode**")
    red_team_mode = st.radio("Red Team Mode", ["Manual Red Team", "Agentic AI Red Team"], index=0, horizontal=True, label_visibility="collapsed")

    aggressiveness = st.select_slider("Agent aggressiveness", options=["Low","Medium","High"], value="Medium")
    max_edits = st.slider("Patch budget: max amendments per round", min_value=1, max_value=5, value=3, step=1)
    max_words = st.slider("Patch budget: max words appended per round", min_value=80, max_value=450, value=250, step=10)

    st.caption("Tip: In workshops, keep edits small (append-only amendments) so you can compare runs across groups.")
    st.divider()

# Round-Based Workshop Mode (optional)
    # ------------------------------
    if wg_mode:
        st.markdown("## 🧪 Working Group Round Mode")
        if "wg_active" not in st.session_state:
            st.session_state.wg_active = False
        if "wg_round" not in st.session_state:
            st.session_state.wg_round = 0
        if "wg_log" not in st.session_state:
            st.session_state.wg_log = []
        if "wg_policy_text" not in st.session_state:
            st.session_state.wg_policy_text = policy_summary
        if "wg_amendments" not in st.session_state:
            st.session_state.wg_amendments = []

        cA, cB, cC = st.columns([1,1,1])
        with cA:
            start_wg = st.button("🟢 Start / Reset Workshop Run", use_container_width=True)
        with cB:
            end_wg = st.button("⛔ End Run", use_container_width=True, disabled=not st.session_state.wg_active)
        with cC:
            dl = st.download_button(
                "⬇️ Download Session JSON",
                data=json.dumps({
                    "policy_title": policy_title,
                    "actors": stakeholders,
                    "log": st.session_state.wg_log,
                    "amendments": st.session_state.wg_amendments,
                    "final_policy_text": st.session_state.wg_policy_text,
                }, indent=2).encode("utf-8"),
                file_name=f"auracelle_charlie_session_{policy_title.replace(' ','_')}.json",
                mime="application/json",
                use_container_width=True,
                disabled=(len(st.session_state.wg_log) == 0),
            )

        if start_wg:
            # Build baseline profiles (re-using API snapshots and defaults)
            api_snaps = {}
            for a in stakeholders:
                api_snaps[a] = fetch_actor_snapshot(a, start_year, end_year, trade_year, policy_title, shock, intensity)
            profiles = build_actor_profiles(stakeholders, api_snaps)
            st.session_state.wg_profiles = profiles
            st.session_state.wg_env = EAGPOEnv(profiles)
            st.session_state.wg_round = 0
            st.session_state.wg_log = []
            st.session_state.wg_amendments = []
            st.session_state.wg_policy_text = policy_summary
            st.session_state.wg_active = True
            st.success("Workshop run initialized. Execute rounds below.")

        if end_wg:
            st.session_state.wg_active = False
            st.info("Run ended. Download JSON if you want to archive the results.")

        if st.session_state.wg_active:
            st.markdown("### 📄 Current Policy Text (with Amendments)")
            st.text_area("Policy Text (read-only during run)", value=st.session_state.wg_policy_text, height=180, key="wg_policy_ro", disabled=True)

            # Red Team inject (manual or agentic)
            st.markdown("### 🧨 Red Team Inject")
            inject_sigma = 0.00
            inject_payload = {}
            if red_team_mode == "Agentic AI Red Team":
                rt = red_team_agent(st.session_state.wg_policy_text, list(stakeholders), st.session_state.wg_round + 1, aggressiveness)
                st.markdown(f"**{rt.get('inject_title','Inject')}**")
                st.write(rt.get("inject",""))
                st.caption(f"Predicted failure mode: **{rt.get('failure_mode','')}**")
                with st.expander("Why it breaks + suggested controls", expanded=False):
                    st.write(rt.get("why_it_breaks",""))
                    st.markdown("**Suggested controls:**")
                    st.write(rt.get("suggested_controls",""))
                inject_choice = st.selectbox("Apply inject intensity", ["None","Light","Moderate","Severe"], index=2)
                inject_sigma = {"None":0.00, "Light":0.02, "Moderate":0.05, "Severe":0.09}[inject_choice]
                inject_payload = {"mode":"agentic", "content":rt, "applied":inject_choice}
            else:
                inj_title = st.text_input("Inject title", value=f"Round {st.session_state.wg_round+1} inject")
                inj_text = st.text_area("Inject description (manual)", height=90, value="Describe the stress event and what governance mechanism it pressures.")
                inject_choice = st.selectbox("Inject intensity", ["None","Light","Moderate","Severe"], index=1)
                inject_sigma = {"None":0.00, "Light":0.02, "Moderate":0.05, "Severe":0.09}[inject_choice]
                inject_payload = {"mode":"manual", "inject_title":inj_title, "inject":inj_text, "applied":inject_choice}

            st.markdown("### 🗳️ Country Actions (Round Decision)")
            # Map actions to stance labels for interpretability
            stance_map = {COOPERATE:"Support", TIGHTEN:"Hedge", DEFECT:"Oppose"}
            action_inputs = {}
            cols = st.columns(min(4, max(1, len(stakeholders))))
            for idx, a in enumerate(stakeholders):
                with cols[idx % len(cols)]:
                    act = st.selectbox(f"{a} action", ["COOPERATE","TIGHTEN","DEFECT"], index=0, key=f"wg_act_{a}_{st.session_state.wg_round}")
                    action_inputs[a] = {"COOPERATE":COOPERATE, "TIGHTEN":TIGHTEN, "DEFECT":DEFECT}[act]
                    st.caption(f"Stance: **{stance_map[action_inputs[a]]}**")

            base_step_sigma = float(base_sigma) + float(inject_sigma)
            execute_round = st.button("➡️ Execute Round", type="primary", use_container_width=True)
            if execute_round:
                env = st.session_state.wg_env
                next_state, rewards, done = env.step({a: action_inputs[a] for a in stakeholders}, shock_sigma=float(base_step_sigma))
                hist = np.array(env.history, dtype=float) if env.history else np.zeros((0,4))
                round_no = st.session_state.wg_round + 1
                # Summarize for Policy Owner
                stance_summary = ", ".join([f"{a}:{stance_map[action_inputs[a]]}" for a in stakeholders])
                metrics = {
                    "tension": float(hist[-1,0]) if hist.shape[0] else None,
                    "stability": float(hist[-1,1]) if hist.shape[0] else None,
                    "sanction_pressure": float(hist[-1,2]) if hist.shape[0] else None,
                    "durability": float(hist[-1,3]) if hist.shape[0] else None,
                }
                st.session_state.wg_log.append({
                    "round": round_no,
                    "stance_summary": stance_summary,
                    "actions": {a: int(action_inputs[a]) for a in stakeholders},
                    "rewards": {k: float(v) for k,v in (rewards or {}).items()},
                    "inject": inject_payload,
                    "shock_sigma": float(base_step_sigma),
                    "metrics": metrics,
                    "timestamp": (__import__('datetime').datetime.utcnow()).isoformat() + "Z",
                })
                st.session_state.wg_round = round_no
                st.success(f"Round {round_no} executed. Metrics updated below.")
                st.rerun()

            # Show latest metrics
            if len(st.session_state.wg_log) > 0:
                last = st.session_state.wg_log[-1]
                m = last.get("metrics", {})
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Durability", f"{(m.get('durability') or 0):.2f}")
                c2.metric("Stability", f"{(m.get('stability') or 0):.2f}")
                c3.metric("Tension", f"{(m.get('tension') or 0):.2f}")
                c4.metric("Sanction Pressure", f"{(m.get('sanction_pressure') or 0):.2f}")

            # Policy Owner amendment (manual or agentic)
            st.markdown("### 🧩 Policy Owner Amendments")
            if len(st.session_state.wg_log) == 0:
                st.info("Execute at least one round to generate amendment suggestions.")
            else:
                last = st.session_state.wg_log[-1]
                round_summary = f"Round {last.get('round')}: {last.get('stance_summary')}. Inject: {inject_payload.get('inject_title', inject_payload.get('content',{}).get('inject_title','')) or ''}"
                if policy_owner_mode == "Agentic AI":
                    po = policy_owner_agent(
                        st.session_state.wg_policy_text,
                        round_summary=round_summary,
                        metrics=last.get("metrics", {}),
                        max_edits=int(max_edits),
                        max_words=int(max_words),
                    )
                    st.markdown("**Suggested amendments (append-only):**")
                    ams = po.get("amendments", [])
                    if not ams:
                        st.write("No amendments suggested.")
                    else:
                        for k,a in enumerate(ams, start=1):
                            st.write(f"{k}. {a}")
                    with st.expander("Rationale", expanded=False):
                        st.write(po.get("rationale",""))

                    apply_po = st.button("✅ Apply Suggested Amendments", use_container_width=True)
                    if apply_po and ams:
                        block = "\n".join([f"- {x}" for x in ams])
                        amend_text = f"\n\nAmendments (Round {last.get('round')}):\n{block}\n"
                        st.session_state.wg_policy_text = (st.session_state.wg_policy_text + amend_text).strip()
                        st.session_state.wg_amendments.append({"round": last.get("round"), "amendments": ams, "rationale": po.get("rationale","")})
                        st.success("Amendments appended to policy text.")
                        st.rerun()
                else:
                    manual_patch = st.text_area("Manual amendment (append-only)", height=110, value="Amendment: ")
                    apply_manual = st.button("✅ Append Manual Amendment", use_container_width=True)
                    if apply_manual and manual_patch.strip():
                        last_round = st.session_state.wg_log[-1].get("round", 0)
                        patch = _word_limit(manual_patch.strip(), int(max_words))
                        amend_text = f"\n\nAmendments (Round {last_round}):\n- {patch}\n"
                        st.session_state.wg_policy_text = (st.session_state.wg_policy_text + amend_text).strip()
                        st.session_state.wg_amendments.append({"round": last_round, "amendments": [patch], "rationale": "Manual"})
                        st.success("Manual amendment appended.")
                        st.rerun()

        st.divider()
# Run controls for selected scenario
    selected = st.session_state.pst_selected
    selected_obj = next((s for s in SCENARIOS if s["id"] == selected), SCENARIOS[0])
    c_run1, c_run2 = st.columns([1, 1])
    with c_run1:
        run_selected = st.button(f"▶ Run Selected: {selected_obj['title']}", type="primary", use_container_width=True, key="pst_run_selected")
    with c_run2:
        run_all = st.button("⚙ Run All Tests", use_container_width=True, key="pst_run_all_top")

    # Execute
    def _execute_one(sc):
        if len(stakeholders) < 2:
            st.warning("Select at least 2 stakeholders.")
            return None

        # Live API snapshots for each stakeholder
        api_snaps = {}
        for a in stakeholders:
            api_snaps[a] = fetch_actor_snapshot(a, start_year, end_year, trade_year, policy_title, shock, intensity)

        # If backend failed for any actor, continue with defaults but surface it.
        failed = [k for k,v in api_snaps.items() if isinstance(v, dict) and v.get("ok") is False]
        if failed:
            st.warning("Backend metrics unavailable for: " + ", ".join(failed) + ". Using default profile values for those actors.")

        profiles = build_actor_profiles(stakeholders, api_snaps)
        out = run_interpretable_marl(
            profiles,
            episodes=int(episodes),
            epsilon=float(epsilon),
            shock_sigma=float(max(base_sigma, sc["shock_sigma"])),
        )

        hist = out["history"]
        last_rewards = out["last_rewards"]
        win = score_win_win(last_rewards)
        vul = count_vulnerabilities(hist)
        rounds = int(hist.shape[0])
        stability_pct = float(hist[-1, 1] * 100.0) if rounds > 0 else 0.0
        durability = float(hist[-1, 3]) if rounds > 0 else 0.0

        status = "passed" if (win >= 60 and durability >= 0.45 and vul <= 3) else "failed"
        return {
            "status": status,
            "win_win_score": float(win),
            "vulnerabilities": int(vul),
            "rounds": int(rounds),
            "stability": float(stability_pct),
            "durability": float(durability),
            "history": hist,
            "durability_by_ep": out["durability_by_ep"],
            "api_snaps": api_snaps,
        }

    if run_selected:
        with st.spinner("Running stress test (live API + interpretable MARL)..."):
            res = _execute_one(selected_obj)
        if res:
            st.session_state.pst_results[selected_obj["id"]] = res
            st.success(f"Completed: {selected_obj['title']}")
            st.rerun()

    if run_all:
        with st.spinner("Running all stress tests (live API + interpretable MARL)..."):
            for sc in SCENARIOS:
                st.session_state.pst_results[sc["id"]] = {"status": "running"}
                st.session_state.pst_results[sc["id"]] = _execute_one(sc) or {"status": "failed"}
        st.success("All tests completed.")
        st.rerun()

    # Visualization block for selected scenario (if exists)
    res = st.session_state.pst_results.get(selected_obj["id"])
    if res and isinstance(res, dict) and "history" in res:
        hist = res["history"]
        dur_ep = res["durability_by_ep"]

        st.markdown("#### Governance Trajectory Plots")
        # Separate matplotlib figures (no subplots)
        fig1 = plt.figure()
        plt.plot(hist[:, 0])
        plt.title("Tension (per round)")
        plt.xlabel("Round")
        plt.ylabel("Tension")
        st.pyplot(fig1, clear_figure=True)

        fig2 = plt.figure()
        plt.plot(hist[:, 1])
        plt.title("Stability (per round)")
        plt.xlabel("Round")
        plt.ylabel("Stability")
        st.pyplot(fig2, clear_figure=True)

        fig3 = plt.figure()
        plt.plot(hist[:, 2])
        plt.title("Sanction Pressure (per round)")
        plt.xlabel("Round")
        plt.ylabel("Sanction Pressure")
        st.pyplot(fig3, clear_figure=True)

        st.markdown("#### Treaty Durability Forecasting Curve")
        fig4 = plt.figure()
        plt.plot(hist[:, 3])
        plt.title("Treaty Durability (per round)")
        plt.xlabel("Round")
        plt.ylabel("Durability")
        st.pyplot(fig4, clear_figure=True)

        st.markdown("#### Durability Convergence Curve")
        fig5 = plt.figure()
        plt.plot(dur_ep)
        plt.title("Durability by Episode (training convergence)")
        plt.xlabel("Episode")
        plt.ylabel("Durability")
        st.pyplot(fig5, clear_figure=True)

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Analysis Results")
    selected = st.session_state.pst_selected
    res = st.session_state.pst_results.get(selected, {})
    if res:
        win = float(res.get("win_win_score", 0.0))
        vul = int(res.get("vulnerabilities", 0))
        rounds = int(res.get("rounds", 0))
        durability = float(res.get("durability", 0.0))

        st.metric("Win-Win Optimization Score", f"{win:.0f}%")
        st.metric("Treaty Durability", f"{durability:.3f}")
        st.metric("Vulnerabilities", f"{vul}")
        st.metric("Rounds Executed", f"{rounds}")




    # (Vulnerability notes & recommendations rendered above when results are available.)

with st.container():
    st.markdown('<div class="ac-bottombar">', unsafe_allow_html=True)
    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 2])
    with b1:
        st.button("💾 Save Test", use_container_width=True, key="pst_save_test")
    with b2:
        st.button("📤 Export Report", use_container_width=True, key="pst_export_report")
    with b3:
        st.button("⚙ Run All Tests", use_container_width=True, key="pst_run_all_bottom")
    with b4:
        st.button("✅ Approve Policy", type="primary", use_container_width=True, key="pst_approve_policy")
    with b5:
        sel = st.session_state.pst_selected
        r = st.session_state.pst_results.get(sel)
        if r and isinstance(r, dict):
            st.caption(f"Selected: **{sel}** · Status: **{r.get('status','ready').upper()}** · Win-Win: **{float(r.get('win_win_score',0)):.0f}%**")
        else:
            st.caption(f"Selected: **{sel}** · Status: **READY**")
    st.markdown('</div>', unsafe_allow_html=True)
