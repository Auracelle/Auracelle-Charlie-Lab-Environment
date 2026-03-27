"""
pages/01_Session_Setup.py — Research consent and participant profile.

Gated by: authentication (requires login).
Writes: session and participant records to SQLite via storage.research_store.
Forwards to: 02_Simulation.py on completion.
"""
import uuid
import streamlit as st
from storage.session_state import init_session_defaults, require_auth
from storage.research_store import init_db, upsert_session, upsert_participant

st.set_page_config(
    page_title="Auracelle Charlie — Session Setup",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("<style>div.block-container{padding-top:0.6rem;}</style>", unsafe_allow_html=True)

init_session_defaults()
require_auth()
init_db()

# Ensure IDs exist
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "participant_id" not in st.session_state:
    st.session_state["participant_id"] = str(uuid.uuid4())

st.title("🔬 Session Setup")

# ── Research consent ──────────────────────────────────────────────────────────
with st.expander("Research Notice & Consent", expanded=True):
    st.write(
        "Auracelle Charlie is a strategic cognition and policy stress-testing simulator. "
        "For research analysis, we record anonymised interaction data, policy selections, "
        "and aggregate indicators (e.g., trust, compliance, alignment, resilience). "
        "You may select 'Prefer not to say' where available."
    )
    consent = st.checkbox(
        "I consent to participate in this research session (required).",
        value=False,
    )

# ── Participant profile ───────────────────────────────────────────────────────
st.subheader("Participant Profile")

col1, col2, col3 = st.columns(3)
with col1:
    gender = st.selectbox(
        "Gender *",
        ["Female", "Male", "Non-binary", "Prefer to self-describe", "Prefer not to say"],
        index=4,
    )
    sector = st.selectbox(
        "Sector / Affiliation *",
        ["Military", "Government", "Industry", "Academia", "Civil Society", "Other", "Prefer not to say"],
        index=6,
    )
    military_status = st.selectbox(
        "Military status *",
        ["Active Duty", "Veteran", "Civilian", "Prefer not to say"],
        index=3,
    )
with col2:
    role_function = st.selectbox(
        "Role function *",
        ["Policy", "Technical", "Legal", "Operations", "Leadership", "Research", "Other", "Prefer not to say"],
        index=7,
    )
    years_experience = st.selectbox(
        "Years in field *",
        ["0–2", "3–5", "6–10", "10+", "Prefer not to say"],
        index=4,
    )
    wargame_experience = st.selectbox(
        "Wargaming / simulation experience *",
        ["None", "Some", "Frequent", "Prefer not to say"],
        index=3,
    )
with col3:
    ai_gov_familiarity = st.selectbox(
        "AI governance familiarity *",
        ["Novice", "Intermediate", "Advanced", "Prefer not to say"],
        index=3,
    )
    age_band = st.selectbox(
        "Age band (optional)",
        ["18–24", "25–34", "35–44", "45–54", "55+", "Prefer not to say"],
        index=5,
    )
    region = st.text_input("Region / Country (optional)", value="")

required_ok = bool(consent)

if st.button("Enter Simulation", disabled=not required_ok, use_container_width=True):
    st.session_state["setup_complete"] = True
    st.session_state["consent"] = True
    st.session_state.setdefault("condition_tag", "unassigned")

    upsert_session(
        st.session_state["session_id"],
        scenario=st.session_state.get("scenario"),
        condition_tag=st.session_state.get("condition_tag"),
    )
    upsert_participant(
        participant_id=st.session_state["participant_id"],
        session_id=st.session_state["session_id"],
        profile={
            "alias":               st.session_state.get("username", ""),
            "consent":             True,
            "gender":              gender,
            "sector":              sector,
            "military_status":     military_status,
            "role_function":       role_function,
            "years_experience":    years_experience,
            "wargame_experience":  wargame_experience,
            "ai_gov_familiarity":  ai_gov_familiarity,
            "age_band":            age_band,
            "region":              region.strip() or None,
        },
    )
    st.switch_page("pages/02_Simulation.py")
