"""
storage/session_state.py — Centralised Streamlit session_state initialisation.

Call init_session_defaults() at the top of streamlit_app.py and any page
that might be reached before the full auth flow completes.
"""
import uuid
import streamlit as st
from config.constants import DEFAULT_EPISODE_LENGTH


def init_session_defaults() -> None:
    """Idempotently initialise all session_state keys Charlie needs."""
    _default("authenticated", False)
    _default("username", "")
    _default("session_id", str(uuid.uuid4()))
    _default("participant_id", str(uuid.uuid4()))
    _default("setup_complete", False)
    _default("consent", False)
    _default("condition_tag", "unassigned")
    _default("scenario", None)

    # Simulation engine state
    _default("round", 1)
    _default("q_table", {})
    _default("adjudicator", None)
    _default("event_log", [])
    _default("round_metrics_trace", [])
    _default("episode_length", DEFAULT_EPISODE_LENGTH)
    _default("stochastic_exploration", False)
    _default("api_data_loaded", False)
    _default("animation_running", False)
    _default("selected_country_click", None)

    # Research session tracking
    _default("research_session_id", str(uuid.uuid4()))


def _default(key: str, value) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def require_auth(page_name: str = "app.py") -> None:
    """Guard: redirect to login if not authenticated."""
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in first.")
        st.switch_page(page_name)
        st.stop()


def require_setup(page_name: str = "pages/01_Session_Setup.py") -> None:
    """Guard: redirect to session setup if consent not given."""
    if not st.session_state.get("setup_complete", False):
        st.info("Please complete Session Setup before entering the simulation.")
        st.switch_page(page_name)
        st.stop()
