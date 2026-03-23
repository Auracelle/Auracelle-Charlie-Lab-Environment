from __future__ import annotations
import uuid
import streamlit as st

DEFAULT_FLAGS = {
    "authenticated": False,
    "setup_complete": False,
    "consent": False,
    "round": 1,
    "event_log": [],
    "round_metrics_trace": [],
    "episode_length": 5,
    "stochastic_exploration": False,
    "api_data_loaded": False,
    "animation_running": False,
    "selected_country_click": None,
}

def ensure_defaults() -> None:
    for key, value in DEFAULT_FLAGS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value

def ensure_session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    return st.session_state["session_id"]
