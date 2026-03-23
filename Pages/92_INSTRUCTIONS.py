import streamlit as st

st.set_page_config(page_title="INSTRUCTIONS", page_icon="📘", layout="wide", initial_sidebar_state="collapsed")

if not st.session_state.get("authenticated", False):
    st.warning("Please log in first.")
    st.switch_page("app.py")

st.header("📘 INSTRUCTIONS")

st.markdown("""
Auracelle Charlie is a **transparent strategic cognition simulator** for testing policy choices under bounded, comparable scenario conditions. It is **not** a black box and **not** a predictive oracle. The platform uses structured user inputs, real-world indicators, and governed scenario logic under **E-AGPO-HT** as the governing law.
""")

with st.expander("1. How to use the environment", expanded=True):
    st.markdown("""
1. **Session Setup**
   Define the user, role, and operating context for the workshop or simulation run.

2. **Simulation**
   Select the policy package, actors, and scenario conditions. Use sliders to express bounded scenario judgments such as trust, readiness, or escalation pressure.

3. **Agentic AI Demo**
   Explore a lightweight agentic sandbox for structured experimentation. This page is separate from the formal governance workflow.

4. **OpenClaw - Agentic AI Demo**
   Use this page for bounded document intake, evidence summarization, draft amendments, narrative responses, and red-team prompts.
   - OpenClaw is **read-only** with respect to scenario context.
   - Outputs are **drafts only**.
   - Nothing becomes official without approval.

5. **Policy Stress-Testing Platform**
   This is the **authoritative assessment workspace**. Use it to evaluate policy choices, compare vulnerabilities, review tradeoffs, and maintain the official session record.

6. **Real-World Data Metrics**
   Pull supporting indicator evidence and contextual data to inform stress-testing and scenario interpretation.

7. **3-D Influence Map**
   Visualize actor relationships, influence pathways, and ecosystem pressures.

8. **Red Team Module**
   Explore adversarial assumptions, cognitive distortion, narrative pressure, and alternative challenge paths.

9. **Mission Console / Admin / Session Tools**
   Review run-state, summaries, and supporting controls where enabled in the notebook build.
""")

with st.expander("2. What each page is for", expanded=False):
    st.markdown("""
- **Simulation** = choose the scenario and bounded inputs.
- **OpenClaw - Agentic AI Demo** = explore evidence and generate drafts safely.
- **Policy Stress-Testing Platform** = conduct the formal assessment.
- **Real-World Data Metrics** = gather contextual evidence.
- **3-D Influence Map** = interpret network and influence structure.
- **Red Team Module** = challenge assumptions and stress cognition.
""")

with st.expander("3. Recommended workflow", expanded=False):
    st.markdown("""
1. Start in **Session Setup**.
2. Move to **Simulation** and define policy and scenario conditions.
3. Use **OpenClaw - Agentic AI Demo** to upload evidence or generate bounded draft support.
4. Review supporting evidence in **Real-World Data Metrics** and the **3-D Influence Map**.
5. Conduct the formal evaluation in the **Policy Stress-Testing Platform**.
6. Use the **Red Team Module** to challenge assumptions and compare alternative interpretations.
7. Record conclusions and iterate.
""")

with st.expander("4. Governance boundaries", expanded=False):
    st.markdown("""
- **E-AGPO-HT** remains the governing law across the environment.
- The platform is designed for **bounded, transparent, comparable scenario inputs**.
- Sliders express scenario conditions; they do **not** replace the governing framework.
- OpenClaw outputs are **assistive drafts**, not official decisions.
- The **Policy Stress-Testing Platform** remains the authoritative location for formal outcomes and session logging.
""")

with st.expander("5. Evidence handling", expanded=False):
    st.markdown("""
- Use uploaded evidence to support interpretation, challenge assumptions, and draft responses.
- Uploaded files on the OpenClaw page should be treated as **evidence objects**, not as authority by themselves.
- Official acceptance of evidence-informed outputs should occur only after review in the formal stress-testing workflow.
""")

st.info("Practical rule: use OpenClaw to explore, summarize, and draft. Use the Policy Stress-Testing Platform to decide, compare, and formally record.")
