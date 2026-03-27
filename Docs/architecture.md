# Auracelle Charlie — Architecture Notes

## Overview

Auracelle Charlie is a multi-layer Streamlit application that separates simulation logic, data access, adjudication, storage, and visualisation into independent packages. The goal is that no page file contains simulation engine logic, and no engine file contains Streamlit calls.

---

## Layer diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Pages                          │
│  01_Session_Setup  02_Simulation  03_Policy_Stress_Testing     │
│  04_Mission_Console  05_Real_World_Data_Metrics  06_Admin       │
└──────────┬──────────────────────────────────┬───────────────────┘
           │ imports                          │ imports
           ▼                                  ▼
┌──────────────────────┐          ┌───────────────────────────────┐
│      engine/         │          │        adjudication/          │
│  scenario_engine.py  │◄─────────│  policy_owner.py              │
│  actors.py           │          │  red_team.py                  │
│  scoring.py          │          │  evaluation.py                │
│  rounds.py           │          └───────────────────────────────┘
│  negotiation.py      │
└──────────┬───────────┘
           │ reads
           ▼
┌──────────────────────┐
│      config/         │
│  actors.yaml         │
│  policies.yaml       │
│  scenarios.yaml      │
│  constants.py        │
└──────────────────────┘

┌──────────────────────┐          ┌───────────────────────────────┐
│      storage/        │          │         data/                 │
│  research_store.py   │          │  loaders.py                   │
│  session_state.py    │          │  (World Bank, CSL, IMF proxy) │
└──────────────────────┘          └───────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                          visuals/                                │
│      maps.py      network_graphs.py      dashboards.py          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key design decisions

### 1. Config-driven actors and policies
All actor definitions live in `config/actors.yaml`. Adding a new actor is a one-line YAML edit — no page code changes required. The same pattern applies to policies (`config/policies.yaml`) and scenarios (`config/scenarios.yaml`).

### 2. Engine is Streamlit-free
`engine/`, `adjudication/`, `data/`, and `visuals/` contain no `import streamlit` statements. This makes them testable with plain pytest and reusable outside the Streamlit context (e.g., a FastAPI backend, a Jupyter notebook, or a batch evaluation script).

### 3. Auth guards are centralised
`storage/session_state.py` provides `require_auth()` and `require_setup()`. Every page that needs a gate calls one of these at the top. No page reimplements the auth check.

### 4. DB path is env-var controlled
`config/constants.DB_PATH` defaults to `data/auracelle_research.db` and is overridable via `CHARLIE_DB_PATH`. The `data/` directory is git-ignored so participant data never enters source control.

### 5. Secrets are never hardcoded
`LOGIN_PASSWORD` and `ADMIN_PIN` read from environment variables with safe development defaults. In production (Streamlit Cloud), these are set via the Secrets panel.

### 6. Agentic agents degrade gracefully
If `OPENAI_API_KEY` is absent, the Policy Owner and Red Team agents fall back to deterministic heuristic outputs. The simulation is fully functional without any API key.

---

## Data flow — one simulation round

```
User action (page)
  │
  ▼
pages/02_Simulation.py
  │  calls
  ▼
engine/rounds.run_round()
  │  builds actions dict, steps EAGPOEnv, updates QAgents
  ▼
engine/scenario_engine.EAGPOEnv.step()
  │  returns (next_state, rewards, done)
  ▼
engine/scoring.round_metrics_snapshot()
  │  computes trust / compliance / alignment / resilience / systemic_risk
  ▼
storage/research_store.log_move()  +  set_outcomes()
  │  writes to SQLite
  ▼
page renders metrics, charts, adjudicator narrative
```

---

## Research database schema

```sql
sessions      (session_id PK, created_at, scenario, condition_tag, started_at, ended_at, completed)
participants  (participant_id PK, session_id FK, created_at, alias, consent, gender, sector,
               military_status, role_function, years_experience, wargame_experience,
               ai_gov_familiarity, age_band, education_band, region)
moves         (id AUTOINCREMENT, session_id FK, participant_id, t, round_num, policy,
               action, notes, state_json)
outcomes      (session_id PK FK, t, trust, compliance, alignment, resilience, unintended_json)
```

---

## External API dependencies

| API | Module | Auth required | Fallback |
|---|---|---|---|
| World Bank (wbgapi) | `data/loaders.py` | None | Baseline YAML values |
| US Consolidated Screening List | `data/loaders.py` | None (rate-limited) | Empty DataFrame |
| OpenAI Chat Completions | `pages/02,03` | `OPENAI_API_KEY` | Heuristic narratives |
| FastAPI research backend | `data/loaders.py` | None (local) | Direct WB calls |

---

## Phase 1 backlog

| Item | Priority | Notes |
|---|---|---|
| FastAPI research backend | High | Restore Cell 13 logic as `backend/main.py`; run with `uvicorn` |
| 3D Influence Map page | Medium | Add `pages/07_3D_Influence_Map.py` using `visuals/maps.py` |
| OpenClaw Agentic AI Demo | Medium | Requires `auracelle_agent_adapter.py` wiring |
| Q-table persistence | Medium | Serialise to SQLite BLOB between sessions |
| SIPRI CSV ingest pipeline | Low | Parse uploaded CSV into `data/sipri_store.py` |
| Unit tests for engine | High | `tests/test_scenario_engine.py`, `tests/test_scoring.py` |
| Streamlit Cloud deployment guide | Medium | `docs/deployment.md` |
| Docker/Compose file | Low | For reproducible deployment |
