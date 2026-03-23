# Architecture Note — Phase 0

## Goal
Move Auracelle Charlie from a notebook-authored prototype to a maintainable repo while preserving current UI and flow.

## Strategy
1. Preserve behavior first.
2. Introduce package seams second.
3. Consolidate duplicated constants and page logic after regression checks.

## Entry points
- `streamlit_app.py`: canonical Streamlit entrypoint
- `app.py`: compatibility shim for legacy imports and page links

## Current layers
- `pages/`: notebook-extracted UI pages
- `engine/`: governance environment / agent logic
- `agpo_data/`: API/data helpers and research storage
- `storage/`: session-state and persistence seam
- `config/`: early single-source-of-truth constants
- `visuals/`, `adjudication/`, `data/`: future extraction seams
