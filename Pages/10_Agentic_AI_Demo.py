
# SPDX-License-Identifier: MIT
import time
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from storage.session_state import require_auth

st.set_page_config(page_title="Agentic AI Demo", layout="wide")

require_auth()

# ------------------------------
# Minimal "aiwargame" sample env
# ------------------------------
# This is a lightweight, self-contained demonstration so it won't clash with your main Simulation logic.
# If your main app exposes shared policy/state helpers later, you can import them here and bypass this local demo.

@dataclass
class Actor:
    name: str
    influence: float = 1.0          # baseline influence (0-3 nominal range)
    compliance: float = 0.5         # nominal "policy compliance / safety posture" (0-1)
    payoff: float = 0.0             # accumulated reward

@dataclass
class Env:
    actors: Dict[str, Actor] = field(default_factory=dict)
    step_count: int = 0
    max_steps: int = 8
    history: List[Dict] = field(default_factory=list)

    def reset(self):
        self.step_count = 0
        self.history = []
        # lightweight baseline
        self.actors = {
            "US": Actor("US", influence=1.2, compliance=0.55),
            "EU": Actor("EU", influence=1.1, compliance=0.65),
            "China": Actor("China", influence=1.25, compliance=0.45),
        }
        return self._obs()

    def _obs(self):
        # Observation is a dict of actor states plus a derived "risk" score
        state = {
            k: {"influence": v.influence, "compliance": v.compliance, "payoff": v.payoff}
            for k, v in self.actors.items()
        }
        # simple aggregate "systemic risk" proxy
        mean_comp = np.mean([v.compliance for v in self.actors.values()])
        mean_inf = np.mean([v.influence for v in self.actors.values()])
        risk = float(max(0.0, 1.2 - (0.6*mean_comp + 0.2*min(1.5, mean_inf))))
        state["_derived"] = {"risk": risk, "t": self.step_count}
        return state

    def step(self, action: str, controlled_actor: str = "US"):
        # Apply an action taken by the "agent" controlling the selected actor.
        # Actions trade off compliance, influence, and a small coalition effect.
        a = self.actors[controlled_actor]

        # stochasticity for realism
        jitter = lambda s: s + random.uniform(-0.01, 0.01)

        coalition_bonus = 0.0
        if action == "Export Controls":
            a.influence = max(0.6, jitter(a.influence + 0.02))
            a.compliance = min(1.0, jitter(a.compliance + 0.04))
        elif action == "Safety Audits":
            a.influence = max(0.6, jitter(a.influence - 0.01))
            a.compliance = min(1.0, jitter(a.compliance + 0.06))
            coalition_bonus = 0.01
        elif action == "Open Data":
            a.influence = min(1.6, jitter(a.influence + 0.03))
            a.compliance = max(0.1, jitter(a.compliance - 0.02))
        elif action == "Joint Standards":
            a.influence = min(1.6, jitter(a.influence + 0.02))
            a.compliance = min(1.0, jitter(a.compliance + 0.03))
            coalition_bonus = 0.02
        else:
            # No-op / hold
            a.influence = jitter(a.influence)
            a.compliance = jitter(a.compliance)

        # Simple coalition effect: others follow a tiny bit
        for k, other in self.actors.items():
            if k == controlled_actor:
                continue
            other.compliance = float(np.clip(other.compliance + coalition_bonus * random.uniform(0.4, 1.2), 0.1, 1.0))

        # Reward = (own influence * 0.6 + own compliance * 0.8) - systemic risk penalty
        obs = self._obs()
        risk = obs["_derived"]["risk"]
        reward = 0.6*a.influence + 0.8*a.compliance - (0.9 * risk)
        a.payoff += reward

        self.step_count += 1
        done = self.step_count >= self.max_steps

        # Log
        self.history.append({
            "t": self.step_count,
            "actor": controlled_actor,
            "action": action,
            "reward": reward,
            "risk": risk,
            "US_infl": self.actors["US"].influence,
            "US_comp": self.actors["US"].compliance,
            "EU_infl": self.actors["EU"].influence,
            "EU_comp": self.actors["EU"].compliance,
            "CN_infl": self.actors["China"].influence,
            "CN_comp": self.actors["China"].compliance,
        })

        return obs, reward, done, {}

# ------------------------------
# A tiny "Agentic AI" controller
# ------------------------------
# A one-step lookahead agent that evaluates each action with a heuristic objective
# and chooses the best. This is intentionally transparent for demo purposes.

ACTIONS = ["Export Controls", "Safety Audits", "Open Data", "Joint Standards", "Hold/No-Op"]

def evaluate_action(env: Env, action: str, actor: str, sims: int = 12):
    # simulate hypothetical outcome for ranking; keep it light-weight
    # Copy a shallow snapshot for Monte Carlo trials
    scores = []
    for _ in range(sims):
        snap = Env()
        # clone state
        snap.actors = {k: Actor(v.name, v.influence, v.compliance, v.payoff) for k, v in env.actors.items()}
        snap.step_count = env.step_count
        obs, reward, _, _ = snap.step(action, controlled_actor=actor)
        # Heuristic: prefer high own reward, lower systemic risk
        srisk = obs["_derived"]["risk"]
        score = reward - 0.3*srisk
        scores.append(score)
    return float(np.mean(scores))

def agent_choose_action(env: Env, actor: str, stochastic: bool = False):
    candidates = []
    for a in ACTIONS:
        s = evaluate_action(env, a, actor)
        candidates.append((a, s))
    candidates.sort(key=lambda x: x[1], reverse=True)
    if stochastic and random.random() < 0.2:
        return random.choice(ACTIONS)
    return candidates[0][0]

# ------------------------------
# UI
# ------------------------------

st.title("🤖 Agentic AI Demo — Sample Game")
st.caption("A transparent, one-step lookahead agent plays a lightweight version of the AI governance wargame.")

left, right = st.columns([2, 1])

with right:
    st.subheader("Agent Controls")
    controlled_actor = st.selectbox("Controlled Actor", ["US", "EU", "China"], index=0)
    horizon = st.slider("Episode Length (steps)", 4, 16, 8, 1)
    stochastic = st.toggle("Enable stochastic exploration (ε≈0.2)", value=True)
    episodes = st.number_input("Batch episodes", min_value=1, max_value=50, value=1, step=1)
    autoplay = st.toggle("Autoplay (fast)", value=False)
    st.markdown("---")
    st.page_link("streamlit_app.py", label="⬅ Back to Home", icon="🏠")

with left:
    st.subheader("Run a Sample Game")
    env = Env()
    env.max_steps = horizon

    run_now = st.button("▶ Play Sample Game")

    if run_now:
        obs = env.reset()
        frames = []
        for t in range(horizon):
            action = agent_choose_action(env, controlled_actor, stochastic=stochastic)
            obs, reward, done, _ = env.step(action, controlled_actor)
            row = {"t": t+1, "action": action, "reward": round(reward, 4), "risk": round(obs["_derived"]["risk"], 4)}
            for k, v in env.actors.items():
                row[f"{k}_influence"] = round(v.influence, 3)
                row[f"{k}_compliance"] = round(v.compliance, 3)
                row[f"{k}_payoff"] = round(v.payoff, 3)
            frames.append(row)
            if not autoplay:
                st.write(f"Step {t+1}: **{action}** → reward {row['reward']}, risk {row['risk']}")
                time.sleep(0.25)
            if done:
                break

        df = pd.DataFrame(frames)
        st.markdown("#### Episode Trace")
        st.dataframe(df, use_container_width=True)

        # Simple summaries
        st.markdown("#### Final Payoffs")
        summary = pd.DataFrame([{"Actor": k, "Payoff": round(v.payoff, 4), "Influence": round(v.influence,3), "Compliance": round(v.compliance,3)}
                                for k, v in env.actors.items()]).sort_values("Payoff", ascending=False)
        st.dataframe(summary, use_container_width=True)

    st.markdown("---")
    st.subheader("Batch Evaluation")
    if st.button("🏃 Run Batch"):
        results = []
        for ep in range(episodes):
            env = Env(); env.max_steps = horizon; env.reset()
            for t in range(horizon):
                a = agent_choose_action(env, controlled_actor, stochastic=stochastic)
                env.step(a, controlled_actor)
            results.append({k: v.payoff for k, v in env.actors.items()})
        res_df = pd.DataFrame(results)
        st.markdown("Average payoff over batch:")
        st.dataframe(pd.DataFrame(res_df.mean()).rename(columns={0:"Avg Payoff"}), use_container_width=True)

