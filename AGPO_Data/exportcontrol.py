"""AGPO Data Package - US Export Controls (Trade.gov CSL) - robust

Trade.gov CSL commonly requires an API key. Provide it via:
- Streamlit secrets: st.secrets["TRADEGOV_API_KEY"]
- Environment variable: TRADEGOV_API_KEY

If no key is available, functions return an empty DataFrame (UI should explain).
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os
import requests
import pandas as pd
import streamlit as st

CSL_URL = "https://api.trade.gov/consolidated_screening_list/search"

def _get_api_key() -> Optional[str]:
    try:
        key = st.secrets.get("TRADEGOV_API_KEY", None)
        if key:
            return str(key).strip()
    except Exception:
        pass
    key = os.getenv("TRADEGOV_API_KEY", "").strip()
    return key or None

@st.cache_data(ttl=86400)
def fetch_consolidated_screening_list(size: int = 200, offset: int = 0) -> pd.DataFrame:
    api_key = _get_api_key()
    if not api_key:
        return pd.DataFrame()

    params: Dict[str, Any] = {"api_key": api_key, "size": int(size), "offset": int(offset)}

    try:
        r = requests.get(CSL_URL, params=params, timeout=15)
        if r.status_code in (401, 403, 429):
            return pd.DataFrame()
        r.raise_for_status()
        payload = r.json() if r.text and r.text.strip() else {}
        results = payload.get("results", []) or []

        records = []
        for item in results:
            addrs = item.get("addresses") or []
            country = (addrs[0].get("country") if addrs else None) or "N/A"
            records.append({
                "name": item.get("name", "N/A"),
                "country": country,
                "source": item.get("source", "N/A"),
                "type": item.get("type", "N/A"),
                "programs": ", ".join(item.get("programs", []) or []),
                "remarks": item.get("remarks", "") or "",
            })
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

def check_entity_sanctions(entity_name: str) -> Optional[pd.DataFrame]:
    df = fetch_consolidated_screening_list()
    if df.empty:
        return None
    return df[df["name"].str.contains(entity_name, case=False, na=False)]


def get_sanctioned_countries(size: int = 200, offset: int = 0) -> list[str]:
    """Return a sorted list of countries appearing in the CSL results.

    Note: CSL is not strictly a "sanctions list" (it aggregates multiple screening sources),
    but this provides a useful governance-friction signal for Auracelle Charlie.
    """
    df = fetch_consolidated_screening_list(size=size, offset=offset)
    if df.empty or "country" not in df.columns:
        return []
    countries = (
        df["country"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    countries = countries[countries.ne("") & countries.ne("N/A")]
    # Normalize common variants
    norm = countries.str.title()
    return sorted(set(norm.tolist()))


def get_export_control_snapshot(actor_iso3: str | None = None, size: int = 200, offset: int = 0) -> dict:
    """Return a lightweight snapshot for the UI/admin layer.

    If TRADEGOV_API_KEY is missing or the API fails, returns enabled=False with a note.
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            "enabled": False,
            "note": "TRADEGOV_API_KEY not set (Streamlit secrets or environment variable).",
            "total_records": 0,
            "unique_countries": 0,
            "actor_iso3": actor_iso3,
        }

    df = fetch_consolidated_screening_list(size=size, offset=offset)
    if df is None or df.empty:
        return {
            "enabled": True,
            "note": "No CSL results returned (API may be rate-limited or empty for this query window).",
            "total_records": 0,
            "unique_countries": 0,
            "actor_iso3": actor_iso3,
        }

    countries = []
    if "country" in df.columns:
        countries = (
            df["country"].dropna().astype(str).str.strip()
        )
        countries = countries[countries.ne("") & countries.ne("N/A")].tolist()

    return {
        "enabled": True,
        "note": "CSL snapshot (not a sanctions list; aggregated screening sources).",
        "total_records": int(len(df)),
        "unique_countries": int(len(set(countries))) if countries else 0,
        "top_countries": pd.Series(countries).value_counts().head(10).to_dict() if countries else {},
        "actor_iso3": actor_iso3,
    }
