
import importlib
import random
from typing import List
import numpy as np
import streamlit as st

def _try_get(module, names: List[str]):
    for n in names:
        if hasattr(module, n):
            return getattr(module, n)
    return None

def _coerce_list(x):
    try:
        return list(x)
    except Exception:
        return None

def load_main_sim_handles():
    try:
        app = importlib.import_module("app")
    except Exception:
        return None
    handles = {}
    handles["policy_options"] = _try_get(app, ["policy_options","POLICY_OPTIONS","policies","POLICY_LIST"])
    handles["policy_effects"] = _try_get(app, ["policy_effect_mappings","policy_effects","POLICY_EFFECTS","policy_effect_map"])
    handles["countries"] = _try_get(app, ["countries","country_list","COUNTRIES","nodes","NODES"])
    handles["roles"] = _try_get(app, ["roles","ROLES"])
    handles["apply_policy"] = _try_get(app, ["apply_policy_effects","apply_policy","apply_effects"])
    handles["get_risk"] = _try_get(app, ["compute_systemic_risk","get_risk","risk_metric"])
    for k in ["policy_options","countries","roles"]:
        if handles.get(k) is not None:
            handles[k] = _coerce_list(handles[k])
    handles["app"] = app
    return handles

def init_state(actors: List[str]):
    if "agent_autoplay_state" not in st.session_state:
        st.session_state.agent_autoplay_state = {
            "t": 0,
            "actors": {a: {"influence": 1.0, "compliance": 0.5, "payoff": 0.0} for a in actors},
            "history": []
        }
    return st.session_state.agent_autoplay_state

def toy_risk(state: dict):
    inf = np.mean([v["influence"] for v in state["actors"].values()])
    comp = np.mean([v["compliance"] for v in state["actors"].values()])
    return float(max(0.0, 1.2 - (0.6*comp + 0.2*min(1.5, inf))))

def derive_risk(handles, state):
    if handles and handles.get("get_risk"):
        try:
            return float(handles["get_risk"](state))
        except Exception:
            pass
    return toy_risk(state)

def step_with_main_effects(handles, state: dict, action: str, controlled_actor: str):
    if handles and handles.get("apply_policy"):
        try:
            new_state = handles["apply_policy"](state, action, controlled_actor)
            st.session_state.agent_autoplay_state = new_state
            risk = derive_risk(handles, new_state)
            a = new_state["actors"][controlled_actor]
            reward = 0.6*a["influence"] + 0.8*a["compliance"] - 0.9*risk
            a["payoff"] += reward
            new_state["t"] = new_state.get("t", 0) + 1
            return reward, risk
        except Exception:
            pass
    pe = None
    if handles and handles.get("policy_effects"):
        pe = handles["policy_effects"]
    if isinstance(pe, dict) and action in pe:
        delta = pe[action]
        a = state["actors"].setdefault(controlled_actor, {"influence": 1.0, "compliance": 0.5, "payoff": 0.0})
        if isinstance(delta, dict):
            if "influence" in delta:
                a["influence"] = float(np.clip(a["influence"] + float(delta["influence"]), 0.1, 2.0))
            if "compliance" in delta:
                a["compliance"] = float(np.clip(a["compliance"] + float(delta["compliance"]), 0.0, 1.0))
        risk = derive_risk(handles, state)
        reward = 0.6*a["influence"] + 0.8*a["compliance"] - 0.9*risk
        a["payoff"] += reward
        state["t"] += 1
        return reward, risk
    # fallback toy step
    a = state["actors"].setdefault(controlled_actor, {"influence": 1.0, "compliance": 0.5, "payoff": 0.0})
    jitter = lambda s: s + random.uniform(-0.01, 0.01)
    if action == "Export Controls":
        a["influence"] = max(0.6, jitter(a["influence"] + 0.02))
        a["compliance"] = min(1.0, jitter(a["compliance"] + 0.04))
    elif action == "Safety Audits":
        a["influence"] = max(0.6, jitter(a["influence"] - 0.01))
        a["compliance"] = min(1.0, jitter(a["compliance"] + 0.06))
    elif action == "Open Data":
        a["influence"] = min(1.6, jitter(a["influence"] + 0.03))
        a["compliance"] = max(0.1, jitter(a["compliance"] - 0.02))
    elif action == "Joint Standards":
        a["influence"] = min(1.6, jitter(a["influence"] + 0.02))
        a["compliance"] = min(1.0, jitter(a["compliance"] + 0.03))
    else:
        a["influence"] = jitter(a["influence"])
        a["compliance"] = jitter(a["compliance"])
    risk = derive_risk(handles, state)
    reward = 0.6*a["influence"] + 0.8*a["compliance"] - 0.9*risk
    a["payoff"] += reward
    state["t"] += 1
    return reward, risk

def get_actions(handles):
    if handles and handles.get("policy_options"):
        return [str(x) for x in handles["policy_options"]]
    return ["Export Controls","Safety Audits","Open Data","Joint Standards","Hold/No-Op"]

def get_actors(handles):
    if handles and handles.get("countries"):
        return [str(x) for x in handles["countries"]]
    return ["US","EU","China"]

def evaluate_action(handles, state, action: str, actor: str, sims: int = 8):
    import copy
    scores = []
    for _ in range(sims):
        s = copy.deepcopy(state)
        reward, risk = step_with_main_effects(handles, s, action, actor)
        scores.append(reward - 0.3*risk)
    return float(np.mean(scores))

def agent_choose_action(handles, state, actor: str, stochastic: bool = False):
    acts = get_actions(handles)
    ranked = [(a, evaluate_action(handles, state, a, actor)) for a in acts]
    ranked.sort(key=lambda x: x[1], reverse=True)
    if stochastic and random.random() < 0.2:
        return random.choice(acts)
    return ranked[0][0]
