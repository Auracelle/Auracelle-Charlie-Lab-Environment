# Auracelle Charlie — Phase 0 GitHub-Ready Refactor

This repo bundle converts the uploaded notebook prototype into a repo-based Streamlit application while preserving the current baseline behavior as closely as possible.

## Preserved baseline behavior

- Login -> Session Setup -> Simulation flow
- Existing notebook-generated pages
- Charlie framing, admin, instructions, mission console, red team, policy stress testing, and agentic pages
- Real-world data helper modules under `agpo_data/`
- Legacy import/file compatibility through `app.py` and `agpo_rl_engine.py`

## Entry point

Run:
```bash
streamlit run streamlit_app.py
```

`app.py` is kept as a compatibility shim because several notebook-extracted files still reference it directly.

## Repo shape

```text
auracelle-charlie-phase0/
├── streamlit_app.py
├── app.py
├── pages/
├── engine/
├── storage/
├── config/
├── visuals/
├── adjudication/
├── data/
├── agpo_data/
├── docs/
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Notes

This is a Phase 0 stabilization handoff, not a full redesign. Heavy page logic remains notebook-faithful to reduce the risk of behavioral drift. New package folders create seams for later extraction and cleanup.
