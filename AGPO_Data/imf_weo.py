"""AGPO Data Package - IMF DataMapper (WEO-style) integration.

Uses IMF DataMapper API v1 (public read) to fetch macro stress indicators.
- Base: https://www.imf.org/external/datamapper/api/v1

Charlie usage:
- GDP growth, inflation, debt-to-GDP as NOF inputs (capacity/stress).
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import requests
import pandas as pd
import streamlit as st

IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"

def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

@st.cache_data(ttl=3600)
def get_series(indicator: str, iso3: str, dataset: str = "WEO") -> pd.DataFrame:
    """Return a tidy DataFrame: Year, Value for indicator@dataset and ISO3."""
    # DataMapper API commonly works as /<indicator>/<ISO3>. Some datasets also accept indicator@DATASET.
    # We try the simpler form first, then fall back to @dataset for compatibility.
    url = f"{IMF_BASE}/{indicator}/{iso3}"
    url_fallback = f"{IMF_BASE}/{indicator}@{dataset}/{iso3}"
    try:
        r = requests.get(url, timeout=25)
        if r.status_code >= 400:
            # try fallback
            r = requests.get(url_fallback, timeout=25)
        r.raise_for_status()
        js = r.json()
        # If response doesn't contain indicator key, try fallback form.
        if not (isinstance(js, dict) and indicator in js):
            r2 = requests.get(url_fallback, timeout=25)
            if r2.ok:
                js2 = r2.json()
                if isinstance(js2, dict) and indicator in js2:
                    js = js2
        if not isinstance(js, dict) or indicator not in js:
            return pd.DataFrame(columns=["Year", "Value"])
        data_block = None
        if isinstance(js, dict):
            if "values" in js and isinstance(js.get("values"), dict):
                data_block = js["values"]
            elif indicator in js:
                data_block = js
        if not isinstance(data_block, dict) or indicator not in data_block:
            return pd.DataFrame(columns=["Year", "Value"])
        iso_block = data_block.get(indicator, {}).get(iso3, {})
        if not isinstance(iso_block, dict):
            return pd.DataFrame(columns=["Year", "Value"])
        rows = []
        for y, v in iso_block.items():
            if str(y).isdigit() and _is_number(v):
                rows.append({"Year": int(y), "Value": float(v)})
        return pd.DataFrame(rows).sort_values("Year")
    except Exception:
        return pd.DataFrame(columns=["Year", "Value"])

def latest_value(df: pd.DataFrame) -> Optional[float]:
    if df is None or df.empty:
        return None
    try:
        return float(df.sort_values("Year", ascending=False).iloc[0]["Value"])
    except Exception:
        return None

def get_latest(indicator: str, iso3: str, dataset: str = "WEO") -> Optional[float]:
    return latest_value(get_series(indicator, iso3, dataset=dataset))

def macro_snapshot(iso3: str) -> Dict[str, Optional[float]]:
    """Opinionated default macro snapshot for Charlie's NOF layer."""
    return {
        "gdp_growth_pct": get_latest("NGDP_RPCH", iso3),
        "inflation_pct": get_latest("PCPIEPCH", iso3),
        "debt_gdp_pct": get_latest("GGXWDG_NGDP", iso3),
    }
