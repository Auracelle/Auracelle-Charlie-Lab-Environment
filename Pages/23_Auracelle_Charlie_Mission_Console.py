import streamlit as st
import numpy as np
import pandas as pd
import copy
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from api_client import post_metrics
from agpo_rl_engine import EAGPOEnv, ACTION_NAMES, COOPERATE, TIGHTEN, DEFECT, institutional_capacity_from_wb
from auracelle_leader_tools import compute_scoreboard, build_leader_brief, build_aar_markdown, build_aar_pdf_bytes, sensitivity_rank

st.set_page_config(page_title="Auracelle Charlie Mission Console", layout="wide")

# --- Console skin (native Streamlit + light CSS; not embedding the HTML mock) ---
st.markdown(r"""
<style>
.block-container {padding-top: 0.8rem; padding-bottom: 1.2rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: .2px;}
.console-card{
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  padding: 14px 14px 12px 14px;
  background: rgba(10,16,34,.25);
}
.pill{
  display:inline-flex; gap:8px; align-items:center;
  padding:7px 10px; border-radius:999px;
  border:1px solid rgba(255,255,255,.12);
  background: rgba(10,16,34,.35);
  font-size: 12px;
}
.dot{width:8px; height:8px; border-radius:999px; display:inline-block;}
.dot.ok{background:#46F0B6;}
.dot.warn{background:#FFCC66;}
.dot.bad{background:#FF6B6B;}
.kpi-grid{
  display:grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap:10px;
}
.kpi{
  border:1px solid rgba(255,255,255,.10);
  border-radius: 16px;
  padding: 10px 12px;
  background: rgba(10,16,34,.28);
}
.kpi .label{font-size:12px; opacity:.85;}
.kpi .value{font-size:22px; font-weight:700; margin-top:2px;}
.kpi .hint{font-size:11px; opacity:.75; margin-top:6px;}
.ticker{
  border:1px solid rgba(255,255,255,.10);
  border-radius: 12px;
  padding: 8px 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 11px;
  background: rgba(10,16,34,.28);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.small-muted{font-size:12px; opacity:.8;}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Session state scaffolding
# -------------------------
if "mc_round" not in st.session_state:
    st.session_state.mc_round = 0
if "mc_phase" not in st.session_state:
    st.session_state.mc_phase = "NEGOTIATION"
if "mc_t0" not in st.session_state:
    st.session_state.mc_t0 = datetime.utcnow()
if "mc_event_log" not in st.session_state:
    st.session_state.mc_event_log = []  # list[str]
if "mc_env" not in st.session_state:
    st.session_state.mc_env = None
if "mc_actor" not in st.session_state:
    st.session_state.mc_actor = None

def log_event(msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    st.session_state.mc_event_log.append(f"[{ts}] {msg}")
    # keep last 200
    st.session_state.mc_event_log = st.session_state.mc_event_log[-200:]

# -------------------------
# Header / top bar
# -------------------------
top_left, top_right = st.columns([1.45, 1.0], vertical_alignment="center")

with top_left:
    st.markdown("## 🎯 Auracelle Charlie Mission Console")
    st.markdown('<div class="small-muted">Strategic cognition view • E-AGPO-HT governance dynamics • Live metrics</div>', unsafe_allow_html=True)

with top_right:
    # We'll set these based on API connectivity and current risk
    # (computed after the API call; placeholders now)
    pass

st.divider()

# -------------------------
# Operator selections (match mock control strip)
# -------------------------
ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([1.0, 1.6, 1.1, 1.2, 1.1])
ACTORS = ["US","China","India","UK","Japan","Brazil","Dubai","NATO"]

actor = ctrl1.selectbox("Actor", ACTORS, index=0)
scenario = ctrl2.selectbox("Scenario", [
    "Interim Final Rule — AI Diffusion",
    "Export Controls — Semiconductor Chokepoints",
    "AI Safety Treaty — Verification & Assurance",
    "Data Localization — Cross-Border Flow Tension"
], index=0)
intensity = ctrl3.slider("Intensity", 0, 100, 62)
shock = ctrl4.selectbox("Shock", ["None","Supply Chain Disruption","Sanctions Escalation","Cyber Incident","Alliance Realignment"], index=0)
trade_year = ctrl5.slider("Trade Year", 2010, 2024, 2020)

start_year, end_year = st.slider("Metrics Window", 2000, 2024, (2010, 2024))

# -------------------------
# Live API call
# -------------------------
api_ok = True
api_err = None
metrics = None
try:
    metrics = post_metrics(actor, start_year, end_year, trade_year, scenario, shock, intensity)
except Exception as e:
    api_ok = False
    api_err = e

# Derive institutional capacity + sanctions index
inst_cap = 0.55
sanctions_index = 0.25
if api_ok and metrics:
    inst_cap = institutional_capacity_from_wb((metrics.get('derived') or {}).get("institutional_capacity"))
    sanctions_index = float((metrics.get('derived') or {}).get("sanctions_index", 0.25))

# -------------------------
# Actor profile (weights + centrality) — replace centrality with your PageRank table when wired
# -------------------------
CENTRALITY = {"US":0.90,"China":0.88,"India":0.65,"UK":0.72,"Japan":0.70,"Brazil":0.55,"Dubai":0.50,"NATO":0.75}.get(actor, 0.60)
RISK_W = {"US":0.65,"China":0.70,"India":0.55,"UK":0.62,"Japan":0.60,"Brazil":0.55,"Dubai":0.58,"NATO":0.66}.get(actor, 0.60)
SAN_S = {"US":0.50,"China":0.40,"India":0.60,"UK":0.52,"Japan":0.45,"Brazil":0.55,"Dubai":0.50,"NATO":0.48}.get(actor, 0.50)

profile = {actor: {
    "institutional_capacity": float(inst_cap),
    "centrality": float(CENTRALITY),
    "risk_weight": float(RISK_W),
    "sanction_sensitivity": float(SAN_S),
}}

# Initialize / swap environment when actor changes
if (st.session_state.mc_env is None) or (st.session_state.mc_actor != actor):
    st.session_state.mc_env = EAGPOEnv(profile)
    st.session_state.mc_actor = actor
    st.session_state.mc_round = 0
    st.session_state.mc_phase = "NEGOTIATION"
    st.session_state.mc_t0 = datetime.utcnow()
    st.session_state.mc_event_log = []
    log_event(f"Session initialized for {actor} | scenario='{scenario}' shock='{shock}' intensity={intensity}")

env = st.session_state.mc_env

# -------------------------
# Status pills (match mock vibe)
# -------------------------
# Risk posture derived from tension + sanctions pressure
risk_posture = "NOMINAL"
risk_dot = "ok"
risk_score = float(env.tension) + float(env.sanction_pressure)*0.6
if risk_score >= 0.85:
    risk_posture, risk_dot = "CRITICAL", "bad"
elif risk_score >= 0.65:
    risk_posture, risk_dot = "ELEVATED", "warn"

feed_label = "NOMINAL" if api_ok else "DEGRADED"
feed_dot = "ok" if api_ok else "bad"

sim_label = "LIVE"
sim_dot = "ok"

tplus = datetime.utcnow() - st.session_state.mc_t0
tplus_str = str(tplus).split(".")[0]

# Render pills in the top-right area
pill_row = f"""
<div style="display:flex; gap:10px; justify-content:flex-end; flex-wrap:wrap;">
  <div class="pill"><span class="dot {sim_dot}"></span>SIMULATION: <b>{sim_label}</b></div>
  <div class="pill"><span class="dot {risk_dot}"></span>RISK POSTURE: <b>{risk_posture}</b></div>
  <div class="pill"><span class="dot {feed_dot}"></span>DATA FEEDS: <b>{feed_label}</b></div>
  <div class="pill">ROUND: <b>{st.session_state.mc_round:02d}</b> • PHASE: <b>{st.session_state.mc_phase}</b> • <span style="font-family:ui-monospace;">T+{tplus_str}</span></div>
</div>
"""
# Put pills on the page (under the divider)
st.markdown(pill_row, unsafe_allow_html=True)

# If API failed, show a console-style error card, but keep the layout
if not api_ok:
    st.markdown('<div class="console-card" style="margin-top:10px;">', unsafe_allow_html=True)
    st.error("Backend connection failed. Start the FastAPI cell first.")
    st.exception(api_err)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -------------------------
# Main console grid
# -------------------------
left, right = st.columns([1.65, 1.0], gap="large")

with left:
    st.markdown('<div class="console-card">', unsafe_allow_html=True)
    st.markdown("### SYNTHETIC OPERATIONS SPACE")
    st.caption("Influence Field • Actors • Edges • Shocks • Negotiation context")

    tab1, tab2, tab3 = st.tabs(["Influence Map", "Geo Map", "Centrality & Deltas"])

    with tab1:
        st.info("Hook point: insert your existing influence network graph here (Plotly / network view).")
        st.write("Current actor centrality (proxy):", round(CENTRALITY, 3))
        st.write("Sanction pressure:", round(env.sanction_pressure, 3))

    with tab2:
        st.info("Hook point: insert your existing Plotly geo map here (Dubai→UAE, NATO marker near Brussels).")

    with tab3:
        st.info("Hook point: show PageRank table, influence deltas, and asymmetry drivers.")
        df = pd.DataFrame([{
            "actor": actor,
            "centrality": CENTRALITY,
            "risk_weight": RISK_W,
            "sanction_sensitivity": SAN_S,
            "institutional_capacity": inst_cap
        }])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="console-card" style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown("### OPERATIONS DIAGNOSTICS")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Institutional capacity", f"{inst_cap:.2f}")
    d2.metric("Sanctions index", f"{sanctions_index:.2f}")
    d3.metric("Internet users %", f"{(metrics.get('latest') or {}).get('internet_users_pct', None) or 0:.2f}")
    d4.metric("Mil exp % GDP", f"{(metrics.get('latest') or {}).get('mil_exp_pct_gdp', None) or 0:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # KPI cards
    st.markdown('<div class="console-card">', unsafe_allow_html=True)
    st.markdown("### KEY GOVERNANCE INDICATORS")

    # Use HTML KPI blocks so it reads like the mock (still native values)
    tension = float(env.tension)
    stability = float(env.stability)
    durability = float(env.durability())

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi"><div class="label">Tension</div><div class="value">{tension:.2f}</div><div class="hint">Escalation pressure + shocks</div></div>
      <div class="kpi"><div class="label">Stability</div><div class="value">{stability:.2f}</div><div class="hint">Institutional resilience</div></div>
      <div class="kpi"><div class="label">Treaty Durability</div><div class="value">{durability:.3f}</div><div class="hint">Forecast curve anchor</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Operator controls card
    st.markdown('<div class="console-card" style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown("### OPERATOR CONTROLS")

    act = st.selectbox("Action", [COOPERATE, TIGHTEN, DEFECT], format_func=lambda a: ACTION_NAMES[a])
    shock_sigma = st.slider("Shock volatility (sigma)", 0.00, 0.10, 0.02, step=0.01)

    b1, b2, b3 = st.columns(3)
    advance = b1.button("Advance Round", type="primary", use_container_width=True)
    mediator = b2.button("Mediator Brief", use_container_width=True)
    pause = b3.button("Pause", use_container_width=True)

    if mediator:
        # --- Leader Decision Brief + Scoreboard + AAR Export ---
        hist = list(env.history) if getattr(env, "history", None) else []
        sb = compute_scoreboard(actor, hist, institutional_capacity=float(inst_cap))
        st.session_state.mc_scoreboard = sb

        # Sensitivity: quick scan across shocks (details abstracted; comparative deltas only)
        shock_sigmas = {
            "None": 0.02,
            "Supply Chain Disruption": 0.05,
            "Sanctions Escalation": 0.07,
            "Cyber Incident": 0.06,
            "Alliance Realignment": 0.04,
        }

        def simulate_end_robustness(shock_name: str) -> int:
            # Fresh env to keep scan comparable and avoid mutating live run
            e = EAGPOEnv({actor: profile[actor]})
            # seed for repeatability within session
            np.random.seed(42)
            random.seed(42)
            for _ in range(max(6, len(hist) or 6)):
                # simple policy: intensity nudges more tighten; otherwise cooperate
                if intensity >= 70:
                    a = TIGHTEN
                elif intensity <= 35:
                    a = COOPERATE
                else:
                    a = random.choice([COOPERATE, TIGHTEN, DEFECT])
                e.step({actor: a}, shock_sigma=float(shock_sigmas.get(shock_name, 0.02)))
            sb2 = compute_scoreboard(actor, list(e.history), institutional_capacity=float(inst_cap))
            return int(sb2.get("robustness_0_100") or 0)

        base_r = simulate_end_robustness("None")
        impacts = {}
        for sname in ["Supply Chain Disruption","Sanctions Escalation","Cyber Incident","Alliance Realignment"]:
            impacts[sname] = float(simulate_end_robustness(sname) - base_r)
        sens_ranked = sensitivity_rank(impacts)
        st.session_state.mc_sensitivity = sens_ranked

        run_state = {
            "actor": actor,
            "scenario": scenario,
            "shock": shock,
            "intensity": intensity,
            "metrics_window": f"{start_year}–{end_year}",
            "trade_year": trade_year,
        }
        brief = build_leader_brief(run_state, sb, sens_ranked)

        st.subheader("Leader Decision Brief")
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown("**" + str(brief.get("header","Leader Decision Brief")) + "**")
            st.markdown("**Decision question:** " + str(brief.get("decision_question", "")))
            st.markdown("**Run context:**")
            for k,v in brief["run_context"].items():
                st.markdown(f"- **{k}:** {v}")
            if brief["now_state"]:
                st.markdown("**Now-state pressures:**")
                for name, val in brief["now_state"]:
                    st.markdown(f"- {name}: {val}/100")
            st.markdown("**Decision triggers (what would change the posture):**")
            for tr in brief["triggers"]:
                st.markdown(f"- {tr}")
        with c2:
            st.markdown("### Quantitative Scoreboard (Decision-Test Outputs)")
            sb_tbl = pd.DataFrame([{
                "Actor": actor,
                "Robustness (0–100)": sb.get("robustness_0_100"),
                "Friction (0–100)": sb.get("friction_0_100"),
                "Evidence threshold (%)": sb.get("evidence_threshold_pct"),
                "Coordination latency (turns)": sb.get("coord_latency_turns"),
            }])
            st.dataframe(sb_tbl, use_container_width=True, hide_index=True)

            st.markdown("**Sensitivity (Top stressors by impact):**")
            if sens_ranked:
                for k,v in sens_ranked[:4]:
                    st.markdown(f"- {k}: Δ {v:+.1f}")
            else:
                st.markdown("- —")

        # --- AAR Export ---
        md = build_aar_markdown(run_state, sb, sens_ranked, st.session_state.get("mc_event_log", []))
        pdf_bytes = build_aar_pdf_bytes(md)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download AAR (Markdown)",
                data=md.encode("utf-8"),
                file_name=f"Auracelle_Charlie_AAR_{actor}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download AAR (PDF)",
                data=pdf_bytes,
                file_name=f"Auracelle_Charlie_AAR_{actor}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    if pause:
        st.warning("Simulation paused (UI placeholder).")

    if advance:
        # Step env
        _, rewards, done = env.step({actor: int(act)}, shock_sigma=shock_sigma)
        st.session_state.mc_round += 1
        st.session_state.mc_phase = "NEGOTIATION" if not done else "POSTURE"
        log_event(f"{actor} action={ACTION_NAMES[int(act)]} reward={rewards[actor]:.3f} shock={shock} intensity={intensity}")
        st.success(f"Round advanced. Reward: {rewards[actor]:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)

    # After-action stream card (ticker + scroll log)
    st.markdown('<div class="console-card" style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown("### AFTER-ACTION STREAM")

    st.markdown(
        f'<div class="ticker">ROUND {st.session_state.mc_round:02d} • {st.session_state.mc_phase} • {actor} • "{scenario}" • shock={shock} • intensity={intensity}</div>',
        unsafe_allow_html=True
    )

    st.text_area("Event Log", "\n".join(st.session_state.mc_event_log[-60:]), height=220)
    st.markdown("</div>", unsafe_allow_html=True)

    # Collapsible live API snapshot (not a primary UI element)
    with st.expander("Live API Snapshot (debug)", expanded=False):
        st.json({"derived": metrics.get("derived", {}), "latest": metrics.get("latest", {})})

# -------------------------
# Trajectory plots (separate figures)
# -------------------------
st.markdown("### Governance Trajectories")
if env.history:
    hist = np.array(env.history)
    fig1 = plt.figure()
    plt.plot(hist[:,0])
    plt.title("Tension Trajectory")
    st.pyplot(fig1)

    fig2 = plt.figure()
    plt.plot(hist[:,1])
    plt.title("Stability Trajectory")
    st.pyplot(fig2)

    fig3 = plt.figure()
    plt.plot(hist[:,2])
    plt.title("Sanction Pressure Trajectory")
    st.pyplot(fig3)

    fig4 = plt.figure()
    plt.plot(hist[:,3])
    plt.title("Treaty Durability Over Rounds")
    st.pyplot(fig4)
else:
    st.info("Advance a round to generate governance trajectories.")
