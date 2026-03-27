"""
pages/04_Mission_Console.py — Strategic cognition live metrics console.

Gated by: authentication + session setup.
Imports: engine.scenario_engine, engine.actors — no inline RL.
"""
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.actors import get_actor_names, build_rl_actor_profiles, load_actor_profiles
from engine.scenario_engine import EAGPOEnv, QAgent, COOPERATE, TIGHTEN, DEFECT, ACTION_NAMES
from engine.scoring import compute_systemic_risk, round_metrics_snapshot
from adjudication.evaluation import aar_summary
from storage.session_state import init_session_defaults, require_auth, require_setup

st.set_page_config(page_title="Auracelle Charlie — Mission Console", layout="wide")

init_session_defaults()
require_auth()
require_setup()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container{padding-top:.8rem;padding-bottom:1.2rem;max-width:1400px;}
h1,h2,h3{letter-spacing:.2px;}
.console-card{border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:14px;background:rgba(10,16,34,.25);}
.pill{display:inline-flex;gap:8px;align-items:center;padding:7px 10px;border-radius:999px;
      border:1px solid rgba(255,255,255,.12);background:rgba(10,16,34,.35);font-size:12px;}
.dot{width:8px;height:8px;border-radius:999px;display:inline-block;}
.dot.ok{background:#46F0B6;} .dot.warn{background:#FFCC66;} .dot.bad{background:#FF6B6B;}
.kpi{border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:10px 12px;background:rgba(10,16,34,.28);}
.kpi .label{font-size:12px;opacity:.85;} .kpi .value{font-size:22px;font-weight:700;margin-top:2px;}
.ticker{border:1px solid rgba(255,255,255,.10);border-radius:12px;padding:8px 10px;
        font-family:monospace;font-size:11px;background:rgba(10,16,34,.28);}
.small-muted{font-size:12px;opacity:.8;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def _def(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

_def("mc_round",     0)
_def("mc_phase",     "NEGOTIATION")
_def("mc_t0",        datetime.utcnow())
_def("mc_event_log", [])
_def("mc_env",       None)
_def("mc_actor",     None)
_def("mc_metrics",   [])


def log_event(msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    st.session_state.mc_event_log.append(f"[{ts}] {msg}")
    st.session_state.mc_event_log = st.session_state.mc_event_log[-200:]


# ── Header ────────────────────────────────────────────────────────────────────
top_left, top_right = st.columns([1.45, 1.0])
with top_left:
    st.markdown("## 🎯 Auracelle Charlie Mission Console")
    st.markdown('<div class="small-muted">Strategic cognition view • E-AGPO-HT governance dynamics • Live metrics</div>', unsafe_allow_html=True)
with top_right:
    elapsed = str(timedelta(seconds=int((datetime.utcnow() - st.session_state.mc_t0).total_seconds())))
    st.markdown(
        f'<span class="pill"><span class="dot ok"></span>Session Active</span>&nbsp;'
        f'<span class="pill">Round {st.session_state.mc_round}</span>&nbsp;'
        f'<span class="pill">⏱ {elapsed}</span>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Controls ──────────────────────────────────────────────────────────────────
ACTORS = get_actor_names()
raw_profiles = load_actor_profiles()

ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([1.0, 1.6, 1.1, 1.2, 1.1])

with ctrl1:
    actor_choice = st.selectbox("Your Actor", ACTORS, index=0, key="mc_actor_sel")

with ctrl2:
    stakeholder_choices = st.multiselect(
        "Active Actors",
        ACTORS,
        default=[ACTORS[0], ACTORS[1], ACTORS[2]] if len(ACTORS) >= 3 else ACTORS,
        key="mc_stakeholders",
    )

with ctrl3:
    action_choice = st.selectbox(
        "Your Action", [ACTION_NAMES[COOPERATE], ACTION_NAMES[TIGHTEN], ACTION_NAMES[DEFECT]],
        index=0, key="mc_action",
    )

with ctrl4:
    shock_sigma = st.slider("Shock sigma", 0.00, 0.10, 0.02, step=0.005, key="mc_sigma")

with ctrl5:
    episodes_quick = st.number_input("Quick-run episodes", 5, 200, 20, step=5, key="mc_episodes")

# ── Action buttons ────────────────────────────────────────────────────────────
b1, b2, b3 = st.columns(3)

with b1:
    if st.button("▶️ Next Round", use_container_width=True):
        if not stakeholder_choices:
            st.warning("Select at least one actor.")
        else:
            # Build / retrieve env
            if st.session_state.mc_env is None:
                profiles = build_rl_actor_profiles(stakeholder_choices)
                st.session_state.mc_env = EAGPOEnv(profiles)
                st.session_state.mc_profiles = profiles

            env: EAGPOEnv = st.session_state.mc_env
            profiles = st.session_state.mc_profiles

            # Map UI action to int
            action_map = {v: k for k, v in ACTION_NAMES.items()}
            human_action = action_map.get(action_choice, COOPERATE)

            # Simple greedy actions for non-human actors
            actions = {}
            for a in stakeholder_choices:
                if a == actor_choice:
                    actions[a] = human_action
                else:
                    # Heuristic: cooperate unless tension high
                    actions[a] = TIGHTEN if env.tension > 0.6 else COOPERATE

            state, rewards, done = env.step(actions, shock_sigma=shock_sigma)
            st.session_state.mc_round += 1

            snapshot = round_metrics_snapshot(
                state,
                actions,
                {a: raw_profiles.get(a, {}).get("position", "") for a in stakeholder_choices},
                env.durability(),
            )
            snapshot["round"] = st.session_state.mc_round
            snapshot["rewards"] = rewards
            st.session_state.mc_metrics.append(snapshot)

            dominant = max(rewards, key=rewards.get) if rewards else "—"
            log_event(f"Round {st.session_state.mc_round}: tension={state[0]:.2f} stability={state[1]:.2f} dominant={dominant}")

            if done:
                log_event("Episode complete — env reset.")
                st.session_state.mc_env = None

with b2:
    if st.button("🔄 Reset Console", use_container_width=True):
        st.session_state.mc_round = 0
        st.session_state.mc_env = None
        st.session_state.mc_metrics = []
        st.session_state.mc_event_log = []
        st.session_state.mc_t0 = datetime.utcnow()
        st.rerun()

with b3:
    if st.button("⚡ Quick Simulation Run", use_container_width=True):
        if stakeholder_choices:
            with st.spinner(f"Running {episodes_quick} episodes…"):
                profiles = build_rl_actor_profiles(stakeholder_choices)
                agents = {a: QAgent(a) for a in profiles}
                env = EAGPOEnv(profiles)
                for ep in range(int(episodes_quick)):
                    state = env.state()
                    done = False
                    while not done:
                        acts = {a: agents[a].choose(state) for a in agents}
                        state, rews, done = env.step(acts, shock_sigma=shock_sigma)
                        for a in agents:
                            agents[a].update(env.history[-2][0:3] if len(env.history) > 1 else state, acts[a], rews[a], state)
                st.session_state.mc_metrics.extend([
                    {
                        "round":            i + 1,
                        "tension":          h[0],
                        "stability":        h[1],
                        "sanction_pressure": h[2],
                        "durability":       h[3],
                    }
                    for i, h in enumerate(env.history)
                ])
                log_event(f"Quick run complete: {episodes_quick} episodes, {len(env.history)} steps.")
        else:
            st.warning("Select at least one actor.")

st.markdown("---")

# ── Main display ──────────────────────────────────────────────────────────────
left, right = st.columns([1.65, 1.0], gap="large")

with left:
    tab1, tab2, tab3 = st.tabs(["📊 Metrics Trace", "🌐 Actor Comparison", "🏆 Scoreboard"])

    with tab1:
        metrics = st.session_state.mc_metrics
        if metrics:
            df = pd.DataFrame(metrics)
            fig = go.Figure()
            for col in ["tension", "stability", "sanction_pressure", "durability"]:
                if col in df.columns:
                    fig.add_trace(go.Scatter(x=df.get("round", list(range(len(df)))), y=df[col],
                                             name=col.replace("_", " ").title(), mode="lines+markers"))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0),
                              legend=dict(orientation="h"), xaxis_title="Round", yaxis_title="Score (0–1)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Advance rounds or run a quick simulation to populate the trace.")

    with tab2:
        actor_data = []
        for name in stakeholder_choices or ACTORS[:5]:
            p = raw_profiles.get(name, {})
            actor_data.append({
                "Actor": name,
                "Influence": p.get("influence", 0),
                "GDP (T)":   p.get("gdp", 0),
                "Mil Exp %": p.get("mil_exp", 0),
                "Internet %": p.get("internet", 0),
                "Alignment": p.get("cultural_alignment", "—"),
            })
        st.dataframe(pd.DataFrame(actor_data), use_container_width=True)

    with tab3:
        metrics_list = st.session_state.mc_metrics
        if metrics_list and isinstance(metrics_list[-1].get("rewards"), dict):
            rews = metrics_list[-1]["rewards"]
            board = pd.DataFrame([{"Actor": k, "Cumulative Reward": round(v, 4)} for k, v in rews.items()])
            board = board.sort_values("Cumulative Reward", ascending=False)
            st.dataframe(board, use_container_width=True)
        else:
            st.info("Scoreboard populates after the first round with multiple actors.")

with right:
    # KPI panels
    metrics_list = st.session_state.mc_metrics
    last = metrics_list[-1] if metrics_list else {}
    tension   = last.get("tension", 0.40)
    stability = last.get("stability", 0.60)
    sancpress = last.get("sanction_pressure", 0.20)
    durability = last.get("durability", 0.0)

    d1, d2 = st.columns(2)
    t_color = "🔴" if tension > 0.7 else ("🟡" if tension > 0.4 else "🟢")
    d1.metric(f"{t_color} Tension",     f"{tension:.0%}")
    d1.metric("🛡️ Stability",           f"{stability:.0%}")
    d2.metric("⚡ Sanction Pressure",   f"{sancpress:.0%}")
    d2.metric("📜 Treaty Durability",   f"{durability:.3f}")

    systemic = compute_systemic_risk(tension, sancpress, stability)
    risk_label = "🔴 CRITICAL" if systemic > 0.65 else ("🟡 ELEVATED" if systemic > 0.35 else "🟢 STABLE")
    st.metric("🌐 Systemic Risk", f"{systemic:.0%}", delta=risk_label)

    st.markdown("---")

    # Phase control
    st.markdown("**📍 Scenario Phase**")
    new_phase = st.radio("Phase", ["NEGOTIATION", "ESCALATION", "DE-ESCALATION", "RESOLUTION"],
                         index=["NEGOTIATION", "ESCALATION", "DE-ESCALATION", "RESOLUTION"].index(st.session_state.mc_phase),
                         key="mc_phase_radio")
    if new_phase != st.session_state.mc_phase:
        st.session_state.mc_phase = new_phase
        log_event(f"Phase transition → {new_phase}")

    # Event ticker
    st.markdown("**📡 Event Log**")
    log_txt = "\n".join(reversed(st.session_state.mc_event_log[-12:]))
    st.text_area("", value=log_txt, height=180, disabled=True, label_visibility="collapsed")

    # AAR quick button
    if st.button("📋 Quick AAR", use_container_width=True):
        aar = aar_summary(
            st.session_state.get("round_metrics_trace", []),
            st.session_state.get("event_log", []),
            "Mission Console Session",
            st.session_state.get("session_id", "—"),
        )
        st.info(aar["summary_text"])
