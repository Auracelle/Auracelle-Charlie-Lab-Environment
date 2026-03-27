"""
Auracelle Charlie — War Gaming Stress-Testing Policy Governance Research Simulation
Phase 0 refactor: notebook → maintainable Streamlit application

Entry point: streamlit run streamlit_app.py
"""
import streamlit as st
from storage.session_state import init_session_defaults
from config.constants import APP_TITLE, APP_ICON, LOGIN_PASSWORD

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_defaults()

st.title(f"{APP_ICON} {APP_TITLE}")

if not st.session_state.get("authenticated", False):
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        st.markdown("### 🎮 Phase 3 Features and Functionality")
        st.markdown("**Capabilities**")

        capabilities = [
            "🌍 World Bank API (GDP, military expenditure, internet penetration)",
            "🚫 US Export Controls API (sanctions screening)",
            "💥 External shock injection system",
            "🎭 Deception detection with real-world data",
            "🗺️ 3-D Influence Map",
            "🛡️ Red Teaming Foresight",
            "🧠 Evans-AGPO-HT Cognitive Science Framework",
        ]
        for c in capabilities:
            st.write(c)

        submit = st.form_submit_button("Login")

    if submit:
        if password == LOGIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.switch_page("pages/01_Session_Setup.py")
        else:
            st.error("Incorrect password. Access denied.")
else:
    st.success(f"Logged in as: {st.session_state.get('username', 'User')}")
    st.info(
        "You are already authenticated. Use the sidebar to navigate, "
        "or continue with the buttons below."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Session Setup", use_container_width=True):
            st.switch_page("pages/01_Session_Setup.py")
    with col2:
        if st.button("Go to Simulation", use_container_width=True):
            st.switch_page("pages/02_Simulation.py")
