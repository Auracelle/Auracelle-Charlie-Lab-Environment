import streamlit as st

st.set_page_config(page_title="COGNITIVE SCIENCE MECHANICS", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

if not st.session_state.get("authenticated", False):
    st.warning("Please log in first.")
    st.switch_page("streamlit_app.py")

st.header("🧠 COGNITIVE SCIENCE MECHANICS")

st.markdown("""
This page provides a **high-level, non-proprietary overview** of how Auracelle Charlie approaches cognition, interpretation, and strategic reasoning in simulation. It is intended to explain the platform logic without exposing protected framework internals.
""")

with st.expander("1. Core idea", expanded=True):
    st.markdown("""
Auracelle Charlie is designed to help users reason through policy choices under uncertainty. It combines:
- structured human judgment,
- bounded scenario inputs,
- comparative policy testing,
- evidence-informed interpretation,
- and transparent review of assumptions.

The aim is to support **strategic cognition**, not to replace human reasoning.
""")

with st.expander("2. Why sliders and bounded inputs are used", expanded=False):
    st.markdown("""
Many governance judgments are qualitative: trust, readiness, coordination, compliance, escalation pressure, or resilience.
Sliders convert those judgments into **bounded, transparent, comparable scenario inputs** so they can be examined across runs.
""")

with st.expander("3. How cognition is represented", expanded=False):
    st.markdown("""
The environment treats cognition as a combination of:
- what an actor perceives,
- how that actor interprets uncertainty,
- what assumptions it prioritizes,
- and how it updates its position as evidence changes.

This supports scenario comparison, red teaming, and deliberative policy testing.
""")

with st.expander("4. How evidence is used", expanded=False):
    st.markdown("""
Real-world indicators and uploaded documents are used to:
- inform scenario context,
- challenge assumptions,
- compare narratives,
- and support explainable assessment.

Evidence helps structure deliberation, but it does not automatically determine the formal outcome.
""")

with st.expander("5. How the platform stays transparent", expanded=False):
    st.markdown("""
Auracelle Charlie is not meant to be a black box. The environment is designed so users can see:
- the selected policy,
- the scenario conditions,
- the evidence being considered,
- the competing interpretations,
- and the final formal assessment path.
""")

with st.expander("6. Relation to governance", expanded=False):
    st.markdown("""
The cognitive science layer supports the broader governance workflow, but the governing authority remains **E-AGPO-HT**.
The platform therefore separates:
- exploratory reasoning,
- assistive drafting,
- and formal policy stress-testing.
""")

st.success("This page is intentionally high-level and workshop-safe. It explains the logic of the environment without disclosing proprietary framework details.")
