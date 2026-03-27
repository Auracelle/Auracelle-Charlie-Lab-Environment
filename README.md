# Auracelle Charlie

**War Gaming Stress-Testing Policy Governance Research Simulation — Phase 0 Release**

> Auracelle Charlie is a strategic cognition and policy stress-testing simulator built on the E-AGPO-HT framework. It enables multi-actor governance wargaming with real-world data integration, adversarial red-team cognition modelling, and a structured research data pipeline.

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/auracelle-charlie.git
cd auracelle-charlie

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set CHARLIE_LOGIN_PASSWORD and ADMIN_PIN at minimum

# 5. Run
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

---

## Navigation

| Page | Purpose |
|---|---|
| **Login** (`streamlit_app.py`) | Authentication gate |
| **01 Session Setup** | Research consent + participant profile |
| **02 Simulation** | Core policy stress-testing wargame |
| **03 Policy Stress Testing** | MARL-based win-win optimisation platform |
| **04 Mission Console** | Live strategic metrics console |
| **05 Real-World Data Metrics** | World Bank / IMF / CSL data integration |
| **06 Admin Dashboard** | Research data viewer + CSV export |

---

## Repository structure

```
auracelle-charlie/
├── streamlit_app.py              # Entry point — login + auth routing
├── pages/
│   ├── 01_Session_Setup.py       # Consent + participant profile
│   ├── 02_Simulation.py          # Core wargame
│   ├── 03_Policy_Stress_Testing.py
│   ├── 04_Mission_Console.py
│   ├── 05_Real_World_Data_Metrics.py
│   └── 06_Admin_Dashboard.py
├── engine/                       # Simulation logic — no Streamlit calls
│   ├── scenario_engine.py        # EAGPOEnv + QAgent (E-AGPO-HT-aligned MARL)
│   ├── actors.py                 # Actor profile loading from config/actors.yaml
│   ├── scoring.py                # Trust / compliance / alignment / resilience
│   ├── rounds.py                 # Round execution orchestrator
│   └── negotiation.py            # Tension index, deception detection, shocks
├── adjudication/                 # Adjudication logic — no Streamlit calls
│   ├── policy_owner.py           # PolicyOwner class
│   ├── red_team.py               # Cognitive attack engine
│   └── evaluation.py             # After Action Review (AAR) generator
├── storage/
│   ├── research_store.py         # SQLite CRUD (sessions / participants / moves / outcomes)
│   └── session_state.py          # Streamlit session_state initialisation + auth guards
├── config/
│   ├── constants.py              # All magic strings + env-var overrides
│   ├── actors.yaml               # Actor definitions (13 actors)
│   ├── policies.yaml             # Policy scenario definitions (8 scenarios)
│   └── scenarios.yaml            # Scenario archetypes (4 scenarios)
├── data/
│   └── loaders.py                # World Bank, CSL, IMF proxy, trade, SDG loaders
├── visuals/
│   ├── maps.py                   # 3D influence map data preparation
│   ├── network_graphs.py         # NetworkX influence graph → Plotly figures
│   └── dashboards.py             # Reusable KPI chart helpers
├── docs/
│   ├── architecture.md           # System architecture notes
│   └── regression_checklist.md  # Regression verification checklist
├── tests/                        # Pytest test stubs
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Configuration

All secrets and runtime parameters are controlled by environment variables. Copy `.env.example` to `.env` and set:

| Variable | Purpose | Default |
|---|---|---|
| `CHARLIE_LOGIN_PASSWORD` | Simulation login password | `charlie2025` |
| `ADMIN_PIN` | Admin dashboard PIN | `1234` |
| `CHARLIE_DB_PATH` | SQLite database path | `data/auracelle_research.db` |
| `CHARLIE_FASTAPI_URL` | Optional FastAPI backend URL | `http://127.0.0.1:8000` |
| `OPENAI_API_KEY` | Enables GPT-4o-mini agentic agents | _(blank = heuristic fallback)_ |

For Streamlit Cloud deployment, set these in the app's **Secrets** panel (`.streamlit/secrets.toml` format), not in `.env`.

---

## Agentic AI agents

The Policy Owner and Red Team agents operate in two modes:

- **Heuristic mode** (default, no API key required): deterministic fallback narratives derived from aggressiveness level and policy context.
- **Agentic mode** (set `OPENAI_API_KEY`): GPT-4o-mini generates contextual negotiation posture, red-team injects, and amendment suggestions within defined patch budgets.

The E-AGPO-HT framework remains the governing law in both modes. Agentic outputs are assistive drafts, not official decisions.

---

## Research data

Participant data is stored locally in SQLite at `data/auracelle_research.db`. This file is excluded from git by `.gitignore`. Administrators can export CSV files from the Admin Dashboard.

**Data collected per session:**
- Anonymised participant profile (consent, gender, sector, role, experience, AI governance familiarity)
- Policy selections and actor choices per round
- Governance outcome metrics (trust, compliance, alignment, resilience) per round

---

## Governing framework

Auracelle Charlie is governed by the **E-AGPO-HT framework** — a proprietary multi-stratum wargaming intelligence architecture developed by Auracelle AI Governance Labs. The framework operates at three levels (aggregate → domain → signal) and drives scoring, adjudication, and scenario dynamics across all simulation modules.

ATT&CK sits beneath E-AGPO-HT as a technical threat input and does not replace the framework.

---

## Phase 0 scope and known limitations

This Phase 0 refactor converts the notebook prototype into a maintainable application structure. The following are known issues to address in Phase 1:

- The FastAPI research backend (notebook Cell 13) is not included in this refactor. The `data/loaders.py` World Bank wrappers provide direct API access as a functional replacement for most use cases.
- The 3D Influence Map page (notebook `pages/20_3D_Influence_Map.py`) is not included in the default navigation. See `visuals/maps.py` for the extracted data-preparation functions; the full Three.js / Plotly 3D page can be added as `pages/07_3D_Influence_Map.py`.
- The OpenClaw Agentic AI Demo (notebook `pages/91_OpenClaw_Agentic_AI_Demo.py`) requires `auracelle_agent_adapter.py` wiring that depends on runtime module introspection. Included as a Phase 1 item.
- Q-table persistence across sessions requires replacing the in-memory dict with a serialised store (pickle or SQLite BLOB).

See `docs/regression_checklist.md` for the full verification checklist.

---

## Licence

Proprietary — Auracelle AI Governance Labs. All rights reserved.

The E-AGPO-HT framework, BGC taxonomy, NOF registry, and associated scoring weights are proprietary intellectual property and are not included in this repository.
