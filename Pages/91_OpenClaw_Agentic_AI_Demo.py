# SPDX-License-Identifier: MIT
import hashlib
import io
from datetime import datetime

import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document

try:
    from auracelle_agent_adapter import load_main_sim_handles
except Exception:
    load_main_sim_handles = None

st.set_page_config(page_title="OpenClaw - Agentic AI Demo", layout="wide")

auth_ok = any(bool(st.session_state.get(k, False)) for k in ("authenticated", "logged_in", "is_authenticated"))
if not auth_ok:
    st.warning("Please log in first (Simulation -> Login).")
    st.stop()

PAGE_NAME = "OpenClaw - Agentic AI Demo"
GOVERNING_LAW = "E-AGPO-HT mathematical intelligence"
ALLOWED_ACTIONS = [
    "Generate narrative response draft",
    "Generate bounded amendment draft",
    "Generate red-team challenge draft",
    "Generate round-summary draft",
]
READ_ONLY_KEYS = [
    "selected_policy",
    "policy_selected",
    "policy_scenario",
    "country_options",
    "roles",
    "research_session_id",
    "simulation_results",
    "risk_scores",
    "stress_test_results",
    "session_log",
]
ACCEPTED_TYPES = ["pdf", "docx", "txt", "doc"]
MAX_UPLOAD_MB = 10
DEFAULT_POLICY_OPTIONS = ['EU Artificial Intelligence Act (AI Act) - Regulation (EU) 2024/1689', 'EU General Data Protection Regulation (GDPR) - Regulation (EU) 2016/679', 'EU Digital Services Act (DSA) - Regulation (EU) 2022/2065', 'EU NIS2 Directive - Directive (EU) 2022/2555', 'UNESCO Recommendation on the Ethics of Artificial Intelligence (2021)', 'OECD Recommendation of the Council on Artificial Intelligence (OECD AI Principles, 2019)', 'American AI Action Plan', 'NATO Article 5']

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def first_present(keys, default=None):
    for key in keys:
        value = st.session_state.get(key)
        if value not in (None, "", [], {}):
            return value
    return default

def resolve_policy_options():
    handles = None
    if load_main_sim_handles is not None:
        try:
            handles = load_main_sim_handles()
        except Exception:
            handles = None
    options = handles.get("policy_options") if handles else None
    if not options:
        for key in ("policy_options", "POLICY_OPTIONS"):
            value = st.session_state.get(key)
            if isinstance(value, list) and value:
                options = value
                break
    if not options:
        options = DEFAULT_POLICY_OPTIONS
    return options

def get_read_only_context():
    context = {}
    for key in READ_ONLY_KEYS:
        if key in st.session_state:
            context[key] = st.session_state.get(key)
    resolved_policy = first_present(
        ["openclaw_selected_policy", "selected_policy", "policy_selected", "policy_scenario"],
        default="No policy selected yet",
    )
    context["selected_policy_resolved"] = resolved_policy
    context["policy_source"] = "OpenClaw selector" if st.session_state.get("openclaw_selected_policy") else "Shared session state"
    return context

def log_governance_event(event_type, detail):
    ledger = st.session_state.setdefault("openclaw_governance_ledger", [])
    ledger.append({
        "timestamp": now_iso(),
        "page": PAGE_NAME,
        "event_type": event_type,
        "detail": detail,
        "governing_law": GOVERNING_LAW,
    })

def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def _safe_preview(text: str, limit: int = 3000) -> str:
    text = (text or "").replace("\x00", " ").strip()
    if len(text) > limit:
        return text[:limit] + "\n\n...[preview truncated]..."
    return text

def extract_text_from_upload(uploaded_file):
    raw = uploaded_file.getvalue()
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    size_bytes = len(raw)
    if size_bytes > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds {MAX_UPLOAD_MB} MB limit.")

    if ext == "txt":
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return raw.decode(encoding), ext
            except Exception:
                pass
        raise ValueError("Could not decode TXT file.")
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text, ext
    if ext == "docx":
        doc = Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs)
        return text, ext
    if ext == "doc":
        raise ValueError("Legacy .doc upload detected. For safe intake, please convert to .docx, .pdf, or .txt first.")
    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

def draft_output(task_type, context, operator_note):
    policy_name = context.get("selected_policy_resolved", "No policy selected yet")
    roles = context.get("roles", [])
    countries = context.get("country_options", [])
    evidence_items = st.session_state.get("openclaw_evidence_buffer", [])
    evidence_names = [item.get("file_name", "uploaded evidence") for item in evidence_items]

    header = [
        f"Task Type: {task_type}",
        f"Policy Context: {policy_name}",
        f"Governing Law: {GOVERNING_LAW}",
        "Authority Status: Draft only - not inserted into official session log",
        "Data Access: Read-only scenario context",
        "Approval Status: Pending human review",
    ]

    evidence_line = (
        f"Evidence Intake: {', '.join(evidence_names[:5])}" if evidence_names else "Evidence Intake: No uploaded evidence in buffer"
    )

    if task_type == "Generate narrative response draft":
        body = [
            "Narrative Draft:",
            f"Under {GOVERNING_LAW}, this draft frames a bounded response to stakeholder objections without altering the official policy text.",
            f"The current scenario centers on: {policy_name}.",
            "Recommended posture: acknowledge institutional concerns, explain rationale, and offer reversible concessions only.",
            evidence_line,
        ]
    elif task_type == "Generate bounded amendment draft":
        body = [
            "Bounded Amendment Draft:",
            f"Proposed amendment language should remain subordinate to {GOVERNING_LAW} and must preserve the original policy intent.",
            "Suggested amendment class: clarification, safeguard, review trigger, or implementation guardrail.",
            "No amendment becomes authoritative until explicit approval is granted.",
            evidence_line,
        ]
    elif task_type == "Generate red-team challenge draft":
        body = [
            "Red-Team Challenge Draft:",
            f"Challenge the policy from the perspective of institutional stress, public legitimacy, and geopolitical exploitation risks linked to {policy_name}.",
            "Focus on second-order effects, loopholes, and narrative attacks.",
            "Outputs remain advisory and must be reviewed before use.",
            evidence_line,
        ]
    else:
        body = [
            "Round Summary Draft:",
            f"This draft summarizes the current scenario around {policy_name}.",
            "It is intended to support structured deliberation and auditability.",
            "It does not modify simulation state or official records.",
            evidence_line,
        ]

    tail = [
        f"Operator Note: {operator_note or 'None provided'}",
        f"Roles in session: {', '.join(map(str, roles)) if roles else 'Not available'}",
        f"Actors/Countries in session: {', '.join(map(str, countries)) if countries else 'Not available'}",
    ]

    return "\n\n".join(["\n".join(header), "\n".join(body), "\n".join(tail)])

st.title("OpenClaw - Agentic AI Demo")
st.caption(
    "Dedicated OpenClaw-facing surface for bounded agentic experimentation in the BSU lab. "
    "E-AGPO-HT remains the governing law and all outputs remain draft-only until approved."
)

with st.expander("Governance posture", expanded=True):
    st.markdown(
        """
- **Governing law:** E-AGPO-HT mathematical intelligence
- **Page role:** isolated OpenClaw-facing demo surface
- **Data access:** read-only scenario context only
- **Outputs:** draft narratives, bounded amendments, red-team suggestions, round summaries
- **Safety rule:** nothing enters the official session log without explicit approval
- **Containment concept:** NemoClaw / OpenShell-style isolation where available
- **Evidence intake:** upload for read-only review; no direct authoritative write-through
        """
    )

left, right = st.columns([1.35, 1.0])

with right:
    st.subheader("Containment and approval")
    nemo_enabled = st.toggle("NemoClaw / OpenShell-style isolation enabled", value=True)
    approval_required = st.toggle("Require approval before official session-log entry", value=True)
    allow_official_write = st.toggle("Allow approved write to official session log", value=False)

    st.markdown("---")
    st.write("**Allowed actions**")
    for item in ALLOWED_ACTIONS:
        st.write(f"- {item}")

with left:
    st.subheader("OpenClaw task surface")
    policy_options = resolve_policy_options()
    inherited_policy = first_present(
        ["openclaw_selected_policy", "selected_policy", "policy_selected", "policy_scenario"],
        default=None,
    )
    default_index = policy_options.index(inherited_policy) if inherited_policy in policy_options else 0
    selected_policy = st.selectbox(
        "Select policy (mirrors Simulation page)",
        policy_options,
        index=default_index,
        help="This selector mirrors the Simulation page policy universe for standalone OpenClaw use. It is read-only context, not the canonical policy authority.",
    )
    st.session_state["openclaw_selected_policy"] = selected_policy

    task_type = st.selectbox("Draft task", ALLOWED_ACTIONS, index=0)
    operator_note = st.text_area(
        "Operator note / bounded instruction",
        placeholder="Example: Draft a response to objections about enforceability while preserving governance safeguards.",
        height=110,
    )

    read_only_context = get_read_only_context()
    with st.expander("Read-only scenario context", expanded=False):
        st.json(read_only_context)

st.markdown("---")
uploader_col, evidence_col = st.columns([1.0, 1.25])

with uploader_col:
    st.subheader("Secure uploader")
    st.caption("Accepted types: PDF, DOCX, TXT. Legacy DOC is flagged for conversion. Uploads are parsed into a read-only evidence buffer.")
    uploaded_file = st.file_uploader(
        "Upload evidence file",
        type=ACCEPTED_TYPES,
        accept_multiple_files=False,
        help="Evidence is held for read-only review on this page and does not automatically enter the official session log.",
    )

    if uploaded_file is not None:
        if st.button("Ingest into Evidence Intake", use_container_width=True):
            try:
                extracted_text, ext = extract_text_from_upload(uploaded_file)
                record = {
                    "timestamp": now_iso(),
                    "file_name": uploaded_file.name,
                    "file_type": ext,
                    "size_bytes": len(uploaded_file.getvalue()),
                    "sha256_short": _hash_bytes(uploaded_file.getvalue()),
                    "preview": _safe_preview(extracted_text),
                    "char_count": len(extracted_text or ""),
                    "status": "read_only_buffered",
                }
                st.session_state.setdefault("openclaw_evidence_buffer", []).append(record)
                log_governance_event(
                    "evidence_buffered",
                    {
                        "file_name": record["file_name"],
                        "file_type": record["file_type"],
                        "sha256_short": record["sha256_short"],
                        "size_bytes": record["size_bytes"],
                    },
                )
                st.success("Evidence uploaded into the read-only buffer.")
            except Exception as e:
                log_governance_event("evidence_buffer_rejected", {"reason": str(e)})
                st.error(str(e))

with evidence_col:
    st.subheader("Evidence Intake")
    evidence_items = st.session_state.get("openclaw_evidence_buffer", [])
    if not evidence_items:
        st.info("No uploaded evidence is currently buffered on this page.")
    else:
        labels = [
            f"{idx + 1}. {item['file_name']} ({item['file_type'].upper()}, {item['char_count']} chars)"
            for idx, item in enumerate(evidence_items)
        ]
        selected_label = st.selectbox("Buffered evidence", labels, index=len(labels) - 1)
        selected_idx = labels.index(selected_label)
        selected_evidence = evidence_items[selected_idx]

        meta1, meta2, meta3 = st.columns(3)
        meta1.metric("File type", selected_evidence["file_type"].upper())
        meta2.metric("Chars extracted", f"{selected_evidence['char_count']:,}")
        meta3.metric("SHA-256 short", selected_evidence["sha256_short"])

        st.text_input("Buffered file", value=selected_evidence["file_name"], disabled=True)
        st.text_area("Read-only evidence preview", value=selected_evidence["preview"], height=280, disabled=True)
        st.caption("Evidence Intake is read-only. Uploaded content may inform drafts but cannot directly alter official Charlie state.")

if st.button("Generate draft output", use_container_width=True):
    generated = draft_output(task_type, read_only_context, operator_note)
    st.session_state["openclaw_pending_draft"] = {
        "timestamp": now_iso(),
        "task_type": task_type,
        "content": generated,
        "nemo_isolation": bool(nemo_enabled),
        "approval_required": bool(approval_required),
        "status": "pending_review",
    }
    log_governance_event(
        "draft_generated",
        {
            "task_type": task_type,
            "nemo_isolation": bool(nemo_enabled),
            "approval_required": bool(approval_required),
            "evidence_count": len(st.session_state.get("openclaw_evidence_buffer", [])),
        },
    )
    st.success("Draft generated and routed to the approval queue.")

st.markdown("---")
st.subheader("Approval queue")
pending = st.session_state.get("openclaw_pending_draft")
if not pending:
    st.info("No OpenClaw draft is currently waiting for review.")
else:
    st.write(f"**Created:** {pending['timestamp']}")
    st.write(f"**Task:** {pending['task_type']}")
    st.write(f"**Status:** {pending['status']}")
    st.text_area("Pending draft content", pending["content"], height=340, key="openclaw_pending_text")

    review_col1, review_col2 = st.columns(2)
    with review_col1:
        if st.button("Approve draft", use_container_width=True):
            pending["status"] = "approved"
            st.session_state["openclaw_pending_draft"] = pending
            st.session_state.setdefault("openclaw_approved_outputs", []).append(dict(pending))
            log_governance_event("draft_approved", {"task_type": pending["task_type"]})
            st.success("Draft approved. It remains separate from the official session log until an explicit write is allowed.")
    with review_col2:
        if st.button("Reject draft", use_container_width=True):
            pending["status"] = "rejected"
            st.session_state["openclaw_pending_draft"] = pending
            log_governance_event("draft_rejected", {"task_type": pending["task_type"]})
            st.warning("Draft rejected. Nothing was written to the official session log.")

st.markdown("---")
st.subheader("Official session-log gate")
approved_outputs = st.session_state.get("openclaw_approved_outputs", [])
if not approved_outputs:
    st.info("No approved OpenClaw drafts are available for official log consideration.")
else:
    latest = approved_outputs[-1]
    st.write(f"Latest approved draft: **{latest['task_type']}** from {latest['timestamp']}")
    st.text_area("Approved draft preview", latest["content"], height=220, key="approved_preview")

    if approval_required and allow_official_write:
        if st.button("Write approved draft to official session log", use_container_width=True):
            official_log = st.session_state.setdefault("session_log", [])
            official_log.append({
                "timestamp": now_iso(),
                "source": PAGE_NAME,
                "task_type": latest["task_type"],
                "content": latest["content"],
                "status": "approved_and_written",
                "governing_law": GOVERNING_LAW,
            })
            log_governance_event("official_log_write", {"task_type": latest["task_type"]})
            st.success("Approved draft written to the official session log.")
    else:
        st.caption("Official log writes stay disabled unless approval is required and explicit write permission is turned on.")

st.markdown("---")
st.subheader("Governance event ledger")
ledger = st.session_state.get("openclaw_governance_ledger", [])
if ledger:
    st.dataframe(pd.DataFrame(ledger), use_container_width=True)
else:
    st.info("No governance events have been recorded on this page yet.")