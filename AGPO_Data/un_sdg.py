"""AGPO Data Package - UN SDG Indicators API integration.

Uses the UNSD SDG API to retrieve SDG indicator observations.
- Base: https://unstats.un.org/SDGAPI/v1/sdg/...

Important:
- UNSD SDG API commonly uses UN M49 numeric geoAreaCode (not ISO3).
- We keep a small actor->M49 mapping in agpo_data.actor_map.

Charlie usage:
- Development inequality / social fragility features to enrich NOF layer.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import requests
import pandas as pd
import streamlit as st

SDG_BASE = "https://unstats.un.org/SDGAPI/v1/sdg"

def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

@st.cache_data(ttl=3600)
def get_series(series_code: str, geo_area_code: int, time_period: Optional[int] = None) -> pd.DataFrame:
    """Fetch a tidy DataFrame: Year, Value for a single SDG series and geo area."""
    url = f"{SDG_BASE}/Series/Data"
    params: Dict[str, Any] = {"seriesCode": series_code, "areaCode": int(geo_area_code), "pageSize": 2000}
    if time_period is not None:
        params["timePeriod"] = int(time_period)
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        data = js.get("data", js)  # sometimes returns {data:[...], ...}
        if not isinstance(data, list):
            return pd.DataFrame(columns=["Year", "Value"])
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if str(item.get("seriesCode", "")).upper() != series_code.upper():
                continue
            if int(item.get("geoAreaCode", -1)) != int(geo_area_code):
                continue
            y = item.get("timePeriod")
            v = item.get("value")
            if y is None or v is None:
                continue
            ys = str(y)
            if ys.isdigit() and _is_number(v):
                rows.append({"Year": int(ys), "Value": float(v)})
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

def get_latest(series_code: str, geo_area_code: int) -> Optional[float]:
    return latest_value(get_series(series_code, geo_area_code))

def social_snapshot(geo_area_code: int) -> Dict[str, Optional[float]]:
    """Opinionated social snapshot for Charlie's NOF layer.

    NOTE: series codes can vary by country/availability; missing series return None.
    """
    return {
        "poverty_rate": get_latest("SI_POV_DAY1", geo_area_code),
        "gini": get_latest("SI_POV_GINI", geo_area_code),
        "unemployment_rate": get_latest("SL_TLF_UEM", geo_area_code),
    }
