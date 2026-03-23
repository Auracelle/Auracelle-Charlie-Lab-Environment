# Regression Checklist — Auracelle Charlie Phase 0

## Access and navigation
- [ ] `streamlit run streamlit_app.py` launches
- [ ] Login page renders
- [ ] Correct password allows entry
- [ ] Incorrect password is rejected
- [ ] Session Setup loads after login
- [ ] Simulation loads after Session Setup

## Simulation
- [ ] Policy dropdown renders
- [ ] Country selectors render
- [ ] Role selectors render
- [ ] Network graph renders
- [ ] Geo map renders
- [ ] PageRank / rankings section renders
- [ ] State survives navigation

## Side pages
- [ ] Red Team Module opens
- [ ] Real-World Data Metrics opens
- [ ] Policy Stress Testing Platform opens
- [ ] Mission Console opens
- [ ] Instructions opens
- [ ] Cognitive Science Mechanics opens
- [ ] Admin Dashboard opens

## Data and secrets
- [ ] App starts without committed secrets
- [ ] Optional integrations fail gracefully when keys are absent
- [ ] No hard-coded secrets remain in tracked files

## Persistence
- [ ] Research store initializes
- [ ] Session ID is created
- [ ] Moves/outcomes can be logged
