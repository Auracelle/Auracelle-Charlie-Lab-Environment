# Auracelle Charlie — Phase 0 Regression Checklist

Use this checklist after running the refactored application for the first time to verify that all baseline behaviours from the notebook prototype are preserved.

Mark each item: ✅ Pass | ❌ Fail | ⚠️ Partial | 🔲 Not yet tested

---

## 1. Authentication & navigation

| # | Test | Expected | Status |
|---|---|---|---|
| 1.1 | Open `http://localhost:8501` | Login form displayed with capability list | 🔲 |
| 1.2 | Enter wrong password | "Incorrect password. Access denied." error | 🔲 |
| 1.3 | Enter correct password (`CHARLIE_LOGIN_PASSWORD`) | Redirect to Session Setup | 🔲 |
| 1.4 | Reload page when already authenticated | "Already authenticated" message with nav buttons | 🔲 |
| 1.5 | Navigate directly to `/02_Simulation` without login | Redirect to login | 🔲 |
| 1.6 | Navigate directly to `/02_Simulation` after login but before setup | Redirect to Session Setup | 🔲 |

---

## 2. Session Setup

| # | Test | Expected | Status |
|---|---|---|---|
| 2.1 | Open Session Setup page | Consent checkbox + participant profile form visible | 🔲 |
| 2.2 | Click "Enter Simulation" without consent | Button disabled | 🔲 |
| 2.3 | Check consent, complete profile, click "Enter Simulation" | Redirect to Simulation page | 🔲 |
| 2.4 | Check SQLite DB after setup | `sessions` and `participants` tables have rows | 🔲 |
| 2.5 | "Prefer not to say" options in all dropdowns | Accepted without error | 🔲 |

---

## 3. Simulation page

| # | Test | Expected | Status |
|---|---|---|---|
| 3.1 | Simulation page loads | Title, policy selector, country selectors visible | 🔲 |
| 3.2 | Policy dropdown — original 8 policies | All 8 original policies listed | 🔲 |
| 3.3 | Policy dropdown — 4 new policies (25 Mar 2026) | Political Declaration, DoD 3000.09, NATO AI Strategy 2024, BIS EAR listed | 🔲 |
| 3.4 | Selecting new policy | Scenario brief displayed correctly | 🔲 |
| 3.3 | Country A / Country B selectors | All 13 actors available | 🔲 |
| 3.4 | Real-world data loads | World Bank spinner appears; no crash on API timeout | 🔲 |
| 3.5 | Policy Position Comparison table | Shows GDP, mil_exp, internet, influence, position for both actors | 🔲 |
| 3.6 | Adjudicator status panel | Tension, Confidence, Alignment, Real Data metrics displayed | 🔲 |
| 3.7 | Deception Detection table | Both actors shown with Risk % and Status | 🔲 |
| 3.8 | "Next Round" button | Round counter increments; metrics trace updates | 🔲 |
| 3.9 | "Reset Episode" button | Round resets to 1; metrics trace cleared | 🔲 |
| 3.10 | Policy Owner expander (Heuristic mode) | Narrative generated without API key | 🔲 |
| 3.11 | Stochastic exploration toggle | Reward varies between rounds when enabled | 🔲 |
| 3.12 | Strategic Analysis section | GDP ratio, mil_exp, internet assessments rendered | 🔲 |
| 3.13 | Metrics trace chart | Appears after 2+ rounds | 🔲 |
| 3.14 | Session metrics written to DB | `moves` and `outcomes` tables have rows after rounds | 🔲 |
| 3.15 | Shock event | Warning box appears (probabilistic; run 10+ rounds at high tension) | 🔲 |

---

## 4. Policy Stress Testing Platform

| # | Test | Expected | Status |
|---|---|---|---|
| 4.1 | Page loads | Three-column layout; top bar with AURACELLE CHARLIE title | 🔲 |
| 4.2 | Technology Domain selector | Dropdown with 5 domains; selection shown in banner | 🔲 |
| 4.3 | Stakeholder multiselect | Actors from config/actors.yaml listed | 🔲 |
| 4.4 | "View / Run" on Coalition Stability | Spinner; results appear in right panel | 🔲 |
| 4.5 | "View / Run" on all 4 scenarios | Each runs without crash; vulnerability count and win-win score shown | 🔲 |
| 4.6 | Win-Win Analysis tab | Bar chart of win-win scores by scenario | 🔲 |
| 4.7 | Implementation Stress tab | Line chart of tension/stability/sanction_pressure/durability | 🔲 |
| 4.8 | Document Stress Test tab | Upload a TXT file; text extracted; stress test runs | 🔲 |
| 4.9 | Generate AAR button | AAR summary text + recommendations displayed | 🔲 |
| 4.10 | Workshop Mode toggle | Workshop controls appear; round cycle runs | 🔲 |
| 4.11 | Red Team inject (heuristic) | Inject title and failure mode shown without API key | 🔲 |
| 4.12 | Policy Owner amendments (heuristic) | 1-3 amendments shown without API key | 🔲 |

---

## 5. Mission Console

| # | Test | Expected | Status |
|---|---|---|---|
| 5.1 | Page loads | Header, pill badges (session active, round, elapsed time) visible | 🔲 |
| 5.2 | "Next Round" | Tension/stability/durability metrics update | 🔲 |
| 5.3 | "Quick Simulation Run" | Metrics trace populates; no crash | 🔲 |
| 5.4 | "Reset Console" | Round resets to 0; metrics cleared; timer resets | 🔲 |
| 5.5 | Metrics Trace tab | Plotly line chart visible after rounds | 🔲 |
| 5.6 | Actor Comparison tab | DataFrame with influence/GDP/mil_exp for selected actors | 🔲 |
| 5.7 | Phase radio | Switching phase logs event to event ticker | 🔲 |
| 5.8 | Event log | Timestamped entries appear after each round | 🔲 |
| 5.9 | Quick AAR button | AAR text displayed in info box | 🔲 |

---

## 6. Real-World Data Metrics

| # | Test | Expected | Status |
|---|---|---|---|
| 6.1 | Page blocked without consent | Redirect to Session Setup | 🔲 |
| 6.2 | Actor selector | All actors listed; ISO3 shown for those with codes | 🔲 |
| 6.3 | World Bank tab — Load button | Charts render for available indicators; graceful warning for missing data | 🔲 |
| 6.4 | Macro tab — Load button | GDP metric shown; note about IMF proxy | 🔲 |
| 6.5 | SDG tab — Load button | Internet penetration metric shown | 🔲 |
| 6.6 | Trade tab — Load button | Trade % GDP shown; Comtrade note displayed | 🔲 |
| 6.7 | Export Controls tab — Load button | CSL data loads or graceful "API unavailable" warning | 🔲 |
| 6.8 | NATO actor | Warning about missing ISO3 code displayed; no crash | 🔲 |

---

## 7. Admin Dashboard

| # | Test | Expected | Status |
|---|---|---|---|
| 7.1 | Page without PIN | "Enter Admin PIN" info message; data not shown | 🔲 |
| 7.2 | Wrong PIN | Data still not shown | 🔲 |
| 7.3 | Correct PIN (`ADMIN_PIN`) | Participant / session / move / outcome counts displayed | 🔲 |
| 7.4 | Composition charts | Gender / sector / military status tables + pie charts | 🔲 |
| 7.5 | Governance Indicators section | Outcomes table displayed (or warning if empty) | 🔲 |
| 7.6 | Raw Data Explorer | All four tables browsable | 🔲 |
| 7.7 | CSV export buttons | Downloads valid CSV files | 🔲 |

---

## 8. Engine & storage unit checks

| # | Test | Expected | Status |
|---|---|---|---|
| 8.1 | `python -c "from engine.scenario_engine import EAGPOEnv"` | No import error | 🔲 |
| 8.2 | `python -c "from engine.actors import load_actor_profiles; print(len(load_actor_profiles()))"` | Prints `13` | 🔲 |
| 8.3 | `python -c "from storage.research_store import init_db; init_db()"` | Creates DB without error | 🔲 |
| 8.4 | `python -c "from data.loaders import get_latest_gdp; print(get_latest_gdp('USA'))"` | Returns a float or None | 🔲 |
| 8.5 | `python -m pytest tests/ -v` | All stub tests pass | 🔲 |

---

## 9. Known Phase 0 gaps (not regressions — documented Phase 1 work)

| # | Gap | Status |
|---|---|---|
| 9.1 | 3D Influence Map page not in default navigation | Documented — Phase 1 |
| 9.2 | OpenClaw Agentic AI Demo not ported | Documented — Phase 1 |
| 9.3 | FastAPI research backend not included | Documented — Phase 1 |
| 9.4 | Q-table not persisted across browser sessions | Documented — Phase 1 |
| 9.5 | SIPRI CSV ingest pipeline not implemented | Documented — Phase 1 |

---

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Principal Investigator | | | |
| Developer | | | |
