"""
pages/03_Policy_Stress_Testing.py — Policy Stress Testing & Win-Win Optimisation Platform.

Gated by: authentication + session setup.
Imports engine.scenario_engine, adjudication.evaluation — no inline RL.
"""
import json
import os
import textwrap
from datetime import date
from io import BytesIO
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from adjudication.evaluation import aar_summary
from engine.actors import get_actor_names, build_rl_actor_profiles
from engine.scenario_engine import EAGPOEnv, QAgent, COOPERATE, TIGHTEN, DEFECT, ACTION_NAMES
from storage.session_state import init_session_defaults, require_auth, require_setup

st.set_page_config(
    page_title="Auracelle Charlie — Policy Stress Testing Platform",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_defaults()
require_auth()
require_setup()

# ── Persistent results state ──────────────────────────────────────────────────
if "pst_results" not in st.session_state:
    st.session_state.pst_results = None
if "wg_active" not in st.session_state:
    st.session_state.wg_active = False
if "wg_amendments" not in st.session_state:
    st.session_state.wg_amendments = []
if "wg_round" not in st.session_state:
    st.session_state.wg_round = 0

ACTORS = get_actor_names()

# ── Agentic helpers ───────────────────────────────────────────────────────────

def _try_openai_chat(system: str, user: str, temperature: float = 0.3) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import requests as _req
        resp = _req.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("AURACELLE_OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": 700,
            },
            timeout=30,
        )
        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip() or None
    except Exception:
        return None


def _word_limit(text: str, max_words: int) -> str:
    words = (text or "").split()
    return (text or "").strip() if len(words) <= max_words else " ".join(words[:max_words]) + " …"


def red_team_agent(policy_text: str, actors: List[str], round_no: int, aggressiveness: str) -> Dict[str, Any]:
    """Return inject + predicted failure mode (governance-level only)."""
    system = (
        "You are the Red Team for a policy stress-testing workshop. "
        "Propose governance failure-mode scenarios and counterfactuals — "
        "policy/governance level only, no technical exploitation. "
        "Return JSON with keys: inject_title, inject, failure_mode, why_it_breaks, suggested_controls."
    )
    user = (
        f"Round {round_no}. Actors: {actors}. Aggressiveness: {aggressiveness}.\n"
        f"Policy draft:\n{policy_text}\n\n"
        "Propose 1 inject scenario and 1 predicted failure mode. Return JSON only."
    )
    out = _try_openai_chat(system, user, temperature=0.4 if aggressiveness == "High" else 0.25)
    if out:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and "inject_title" in data:
                return data
        except Exception:
            pass

    # Heuristic fallback
    library = {
        "Low":    ("Ambiguity & compliance drift",  "Compliance gaming",        "Vague definitions allow differential interpretation.",        "Add measurable thresholds; tiered compliance."),
        "Medium": ("Coalition fracture under enforcement", "Coalition fracture", "Uneven enforcement; allies disagree; non-aligned hedge.",    "Graduated enforcement; mutual recognition; capacity support."),
        "High":   ("Retaliation + forum shopping",  "Trust collapse",           "Actors retaliate; firms relocate; reporting politicised.",    "Safe harbor reporting; independent escalation channel."),
    }
    title, mode, why, controls = library.get(aggressiveness, library["Medium"])
    return {
        "inject_title": title,
        "inject": f"Stress event aligned with '{title}' pressuring enforcement among {actors}.",
        "failure_mode": mode,
        "why_it_breaks": why,
        "suggested_controls": controls,
    }


def policy_owner_agent(
    policy_text: str, round_summary: str, metrics: Dict[str, Any],
    max_edits: int, max_words: int,
) -> Dict[str, Any]:
    """Return 1–3 targeted append-only amendments (bounded)."""
    system = (
        "You are the Policy Owner in a governance wargaming workshop. "
        "Preserve policy intent and propose small, specific append-only amendments. "
        "Return JSON with keys: intent_preserved, amendments (list), rationale."
    )
    user = (
        f"Round summary: {round_summary}\nMetrics: {json.dumps(metrics)}\n\n"
        f"Policy draft:\n{policy_text}\n\n"
        f"Propose up to {max_edits} amendments. Total amendment text under {max_words} words (append-only)."
    )
    out = _try_openai_chat(system, user, temperature=0.3)
    if out:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and "amendments" in data:
                ams = data["amendments"]
                if isinstance(ams, str):
                    ams = [a.strip() for a in ams.split("\n") if a.strip()]
                data["amendments"] = [_word_limit(a, max_words // max(max_edits, 1)) for a in ams[:max_edits]]
                return data
        except Exception:
            pass

    ams = [
        "Add a phased review gate at 12 months post-implementation.",
        "Include an explicit safe-harbor clause for voluntary incident disclosure.",
        "Require graduated sanctions tied to documented violation severity.",
    ][:max_edits]
    return {
        "intent_preserved": True,
        "amendments": ams,
        "rationale": "Targeted clarifications to reduce hedging and improve durability.",
    }


# ── MARL helpers ──────────────────────────────────────────────────────────────

def run_interpretable_marl(
    actor_profiles: dict,
    episodes: int = 80,
    epsilon: float = 0.18,
    shock_sigma: float = 0.03,
) -> dict:
    agents = {a: QAgent(a, epsilon=epsilon) for a in actor_profiles}
    durability_by_ep = []
    last_hist = None
    last_rewards: dict = {}

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
        last_hist = env.history[:]
        last_rewards = rewards  # type: ignore[assignment]

    return {
        "durability_by_ep": np.array(durability_by_ep, dtype=float),
        "history": np.array(last_hist, dtype=float) if last_hist else np.zeros((0, 4)),
        "last_rewards": last_rewards,
    }


def score_win_win(last_rewards: dict) -> float:
    if not last_rewards:
        return 0.0
    vals = np.array(list(last_rewards.values()), dtype=float)
    raw = float(np.mean(vals) - 0.5 * np.std(vals))
    return float(np.clip(50 + 50 * raw, 0, 100))


def count_vulnerabilities(history: np.ndarray) -> int:
    if history.size == 0:
        return 0
    vul = 0
    if history[-1, 0] > 0.70:  # tension
        vul += 2
    if history[-1, 2] > 0.35:  # sanction_pressure
        vul += 2
    if history[-1, 3] < 0.45:  # durability
        vul += 2
    return vul


SCENARIOS = [
    {"id": "coalition_stability", "title": "Coalition Stability",     "icon": "🤝", "desc": "Tests if agreements hold under asymmetric incentives.",        "shock_sigma": 0.03},
    {"id": "free_rider_detection","title": "Free Rider Detection",    "icon": "🎭", "desc": "Identifies actors who benefit without contributing.",           "shock_sigma": 0.035},
    {"id": "sanction_escalation", "title": "Sanction Escalation",    "icon": "⚡", "desc": "Stress-tests network-weighted sanction propagation.",           "shock_sigma": 0.04},
    {"id": "shock_resilience",    "title": "Shock Resilience",       "icon": "🌪️", "desc": "Injects stochastic shocks to evaluate recovery dynamics.",      "shock_sigma": 0.06},
]


def _extract_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(raw))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            return "[PDF text extraction failed — install PyPDF2]"
    if name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return "[DOCX text extraction failed — install python-docx]"
    return "[Unsupported file type]"


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.ac-topbar{background:linear-gradient(135deg,#1e293b 60%,#0f172a);padding:18px 24px;border-radius:12px;margin-bottom:12px;}
.ac-title{font-size:1.55rem;font-weight:900;color:#f1f5f9;letter-spacing:.04em;}
.ac-subtitle{font-size:.83rem;color:#94a3b8;margin-top:2px;}
.ac-card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:10px;}
.ac-badge{font-size:.7rem;font-weight:700;background:#0f172a;color:#94a3b8;border:1px solid #334155;border-radius:999px;padding:4px 10px;letter-spacing:.08em;}
.ac-badge-testing{background:#1e3a5f;color:#60a5fa;border-color:#2563eb;}
.ac-muted{font-size:.8rem;color:#64748b;}
.ac-pill{display:inline-flex;align-items:center;gap:6px;background:#022c22;color:#4ade80;border:1px solid #166534;border-radius:999px;padding:3px 10px;font-size:.72rem;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
with st.container():
    c1, c2 = st.columns([2.2, 1.2])
    with c1:
        st.markdown("""
        <div class="ac-topbar">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="font-size:1.9rem;">🧬</div>
            <div>
              <div class="ac-title">AURACELLE CHARLIE</div>
              <div class="ac-subtitle">Policy Stress Testing &amp; Win-Win Optimisation Platform</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    with c2:
        tech = st.selectbox(
            "Technology Domain",
            ["🤖 AI Governance", "🧬 BioTech", "⚛️ Nuclear", "🛰️ Space", "🧪 Quantum"],
            index=0, label_visibility="collapsed",
        )
        st.markdown('<span class="ac-pill"><span style="width:8px;height:8px;border-radius:999px;background:#10b981;display:inline-block;"></span>STRESS TEST READY</span>', unsafe_allow_html=True)

# ── Main 3-column layout ──────────────────────────────────────────────────────
left, mid, right = st.columns([1.15, 2.2, 1.15], gap="medium")

with left:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Policy Input")
    uploaded      = st.file_uploader("Upload Policy Draft (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    policy_title  = st.text_input("Policy Title", value="International AI Safety Standards")
    policy_summary = st.text_area(
        "Policy Summary / Draft", height=140,
        value="A cooperative verification and assurance framework for frontier AI systems, "
              "including disclosure, audits, incident response, and enforcement incentives.",
    )
    if uploaded:
        extracted = _extract_text(uploaded)
        if extracted and extracted.strip():
            st.caption(f"✅ Extracted {len(extracted.split())} words from {uploaded.name}")
            policy_summary = extracted[:3000]  # cap to context budget

    st.divider()
    st.markdown("### 🤝 Stakeholders")
    stakeholders = st.multiselect("Select stakeholders", ACTORS, default=["United States", "China", "India"])
    st.caption("Tip: keep to 3-5 actors for interpretability and speed.")

    st.divider()
    st.markdown("### ⚙️ Test Parameters")
    start_year, end_year = st.slider("Metrics window", 2000, 2024, (2000, 2024), step=1)
    trade_year  = st.slider("Trade year", 2010, 2024, 2024, step=1)
    intensity   = st.slider("Policy intensity", 0, 100, 62, step=1)
    shock       = st.selectbox("Baseline shock", ["None", "SupplyChain", "CyberIncident", "BioEvent", "ConflictEscalation"], index=0)

    st.divider()
    st.markdown("### 🧠 Training")
    episodes  = st.slider("Episodes", 20, 500, 120, step=10)
    epsilon   = st.slider("Exploration epsilon", 0.00, 0.50, 0.18, step=0.01)
    base_sigma = st.slider("Shock volatility (sigma)", 0.00, 0.10, 0.03, step=0.005)
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    badge = "TESTING" if st.session_state.pst_results else "READY"
    badge_cls = "ac-badge-testing" if badge == "TESTING" else ""
    tech_clean = tech.split(" ", 1)[-1] if " " in tech else tech
    st.markdown(
        f"""<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
          <div>
            <div style="font-size:1.45rem;font-weight:800;">{policy_title}</div>
            <div class="ac-muted" style="margin-top:4px;">
              🌐 Technology: <strong>{tech_clean}</strong>
              &nbsp;&nbsp;🤝 Stakeholders: <strong>{len(stakeholders)} Selected</strong>
              &nbsp;&nbsp;📅 Test Date: <strong>{date.today().isoformat()}</strong>
            </div>
          </div>
          <div class="ac-badge {badge_cls}">{badge}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Robustness Tests", "Unintended Consequences", "Win-Win Analysis", "Implementation Stress", "Document Stress Test"])

    def scenario_status(sid):
        r = st.session_state.pst_results
        if not r:
            return "⚪ Not run"
        d = r.get(sid, {})
        return "✅ Stable" if d.get("vulnerabilities", 10) < 3 else ("⚠️ Fragile" if d.get("vulnerabilities", 10) < 6 else "🔴 Critical")

    def render_scenario_grid():
        cols = st.columns(2)
        for i, sc in enumerate(SCENARIOS):
            with cols[i % 2]:
                st.markdown(
                    f"**{sc['icon']} {sc['title']}**  \n{sc['desc']}  \n*Status: {scenario_status(sc['id'])}*"
                )
                run = st.button("View / Run", key=f"run_{sc['id']}", use_container_width=True)
                if run:
                    if not stakeholders:
                        st.warning("Select at least one stakeholder.")
                    else:
                        with st.spinner(f"Running {sc['title']}…"):
                            profiles = build_rl_actor_profiles(stakeholders)
                            res = run_interpretable_marl(profiles, episodes=episodes, epsilon=epsilon, shock_sigma=sc["shock_sigma"])
                        if st.session_state.pst_results is None:
                            st.session_state.pst_results = {}
                        st.session_state.pst_results[sc["id"]] = {
                            "vulnerabilities": count_vulnerabilities(res["history"]),
                            "win_win": score_win_win(res["last_rewards"]),
                            "durability": float(res["durability_by_ep"][-1]) if res["durability_by_ep"].size > 0 else 0.0,
                            "history": res["history"].tolist(),
                            "scenario": sc["title"],
                        }
                        st.rerun()

    with tabs[0]:
        render_scenario_grid()

    with tabs[1]:
        r = st.session_state.pst_results
        if not r:
            st.info("Run a scenario to see unintended consequence analysis.")
        else:
            for sid, data in r.items():
                st.markdown(f"**{data.get('scenario', sid)}** — Vulnerabilities: {data.get('vulnerabilities', '—')}")

    with tabs[2]:
        r = st.session_state.pst_results
        if not r:
            st.info("Run a scenario to see win-win analysis.")
        else:
            scores = {data.get("scenario", sid): data.get("win_win", 0) for sid, data in r.items()}
            fig = go.Figure(go.Bar(
                x=list(scores.keys()), y=list(scores.values()),
                marker_color=["#22d3ee" if v >= 50 else "#f87171" for v in scores.values()],
            ))
            fig.update_layout(yaxis_range=[0, 100], yaxis_title="Win-Win Score", height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        r = st.session_state.pst_results
        if not r:
            st.info("Run a scenario to see implementation stress analysis.")
        else:
            for sid, data in r.items():
                hist = np.array(data.get("history", []))
                if hist.size > 0:
                    st.markdown(f"**{data.get('scenario', sid)}**")
                    fig = go.Figure()
                    labels = ["Tension", "Stability", "Sanction Pressure", "Durability"]
                    for i, label in enumerate(labels):
                        fig.add_trace(go.Scatter(y=hist[:, i], name=label, mode="lines"))
                    fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.markdown("**Document Stress Test** — Upload a policy document to stress-test against the MARL engine.")
        doc_upload = st.file_uploader("Upload policy document", type=["pdf", "docx", "txt"], key="doc_stress_upload")
        if doc_upload:
            doc_text = _extract_text(doc_upload)
            if doc_text.strip():
                st.text_area("Extracted Policy Text", value=doc_text[:2000], height=200, disabled=True)
                if st.button("Run Document Stress Test"):
                    if stakeholders:
                        with st.spinner("Stress-testing uploaded document…"):
                            profiles = build_rl_actor_profiles(stakeholders)
                            res = run_interpretable_marl(profiles, episodes=max(episodes, 40))
                        vul = count_vulnerabilities(res["history"])
                        st.metric("Vulnerabilities detected", vul)
                        st.metric("Win-Win Score", f"{score_win_win(res['last_rewards']):.1f}")
                    else:
                        st.warning("Select at least one stakeholder first.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Results Summary")
    r = st.session_state.pst_results
    if r:
        for sid, data in r.items():
            col_a, col_b = st.columns(2)
            col_a.metric(data.get("scenario", sid)[:20], f"Vul: {data.get('vulnerabilities', '—')}")
            col_b.metric("Win-Win", f"{data.get('win_win', 0):.0f}")
        if st.button("🔄 Clear All Results", use_container_width=True):
            st.session_state.pst_results = None
            st.rerun()
    else:
        st.info("No results yet. Run a scenario from the test panel.")
    st.markdown("</div>", unsafe_allow_html=True)

    # AAR Summary
    st.markdown('<div class="ac-card">', unsafe_allow_html=True)
    st.markdown("### 📋 After Action Review")
    if st.button("Generate AAR", use_container_width=True):
        aar = aar_summary(
            st.session_state.get("round_metrics_trace", []),
            st.session_state.get("event_log", []),
            policy_title,
            st.session_state.get("session_id", "—"),
        )
        st.markdown(aar["summary_text"])
        for rec in aar["recommendations"]:
            st.info(rec)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Workshop Mode ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎓 Workshop Mode")
wg_mode = st.toggle(
    "Enable Round-Based Workshop Mode",
    value=st.session_state.wg_active,
    help="Step through rounds with manual/agentic Red Team and Policy Owner amendments.",
)
if wg_mode != st.session_state.wg_active:
    st.session_state.wg_active = wg_mode

aggressiveness = st.select_slider("Red Team aggressiveness", ["Low", "Medium", "High"], value="Medium")
max_edits      = st.slider("Patch budget: max amendments per round", 1, 5, 3)
max_words      = st.slider("Max words per amendment", 30, 200, 80)
st.caption("In workshops, keep edits small (append-only) so you can compare runs across groups.")

if st.session_state.wg_active:
    col_start, col_end = st.columns(2)
    with col_start:
        if st.button("🟢 Start / Reset Workshop Run", use_container_width=True):
            st.session_state.wg_round = 0
            st.session_state.wg_amendments = []
            st.session_state.wg_policy_text = policy_summary
    with col_end:
        if st.button("⛔ End Run", use_container_width=True, disabled=not st.session_state.wg_active):
            st.session_state.wg_active = False
            st.rerun()

    wg_policy = st.session_state.get("wg_policy_text", policy_summary)
    st.text_area("Policy Text (read-only during run)", value=wg_policy, height=180, disabled=True)

    if st.button("▶️ Next Workshop Round", use_container_width=True):
        st.session_state.wg_round += 1
        rnd = st.session_state.wg_round
        with st.spinner(f"Running workshop round {rnd}…"):
            rt_result = red_team_agent(wg_policy, stakeholders, rnd, aggressiveness)
            po_result = policy_owner_agent(wg_policy, json.dumps(rt_result), {}, max_edits, max_words)
        st.markdown(f"#### Round {rnd} — Red Team Inject")
        st.warning(f"**{rt_result.get('inject_title')}**\n\n{rt_result.get('inject')}\n\n"
                   f"**Failure mode:** {rt_result.get('failure_mode')}\n\n"
                   f"**Why it breaks:** {rt_result.get('why_it_breaks')}\n\n"
                   f"**Suggested controls:** {rt_result.get('suggested_controls')}")
        st.markdown("#### Policy Owner Response")
        for am in po_result.get("amendments", []):
            st.success(f"✏️ {am}")
        st.session_state.wg_amendments.extend(po_result.get("amendments", []))

    if st.session_state.wg_amendments:
        with st.expander(f"📝 Amendment log ({len(st.session_state.wg_amendments)} entries)", expanded=False):
            for i, am in enumerate(st.session_state.wg_amendments, 1):
                st.write(f"{i}. {am}")
