"""AGPO Data Package - Trade leverage (UN Comtrade + optional WTO hooks).

Primary: UN Comtrade (legacy REST-style /api/get).

Design principle:
- Degrade gracefully if endpoint / auth changes: return empty DataFrames / None.
- Keep outputs as tidy DataFrames + small snapshot dicts for Charlie's NOF layer.

Optional: WTO APIs typically require a subscription key; we leave a future hook.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import os
import requests
import pandas as pd
import streamlit as st

# Legacy UN Comtrade endpoint:
COMTRADE_BASE = "https://comtrade.un.org/api/get"

def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

@st.cache_data(ttl=3600)
def comtrade_query(
    reporter: int,
    partner: int = 0,
    year: int = 2022,
    trade_flow: str = "all",
    max_records: int = 500,
    commodity_code: str = "TOTAL",
) -> pd.DataFrame:
    """Query Comtrade and return a DataFrame (may be empty)."""
    params = {
        "max": int(max_records),
        "type": "C",
        "freq": "A",
        "px": "HS",
        "ps": str(year),
        "r": int(reporter),
        "p": int(partner),
        "rg": trade_flow,
        "cc": commodity_code,
        "fmt": "json",
    }
    try:
        r = requests.get(COMTRADE_BASE, params=params, timeout=35)
        r.raise_for_status()
        js = r.json()
        data = js.get("dataset", js.get("data", []))
        if not isinstance(data, list):
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def total_trade_value_usd(df: pd.DataFrame) -> Optional[float]:
    if df is None or df.empty:
        return None
    col = None
    for c in ["TradeValue", "tradeValue", "Trade Value (US$)"]:
        if c in df.columns:
            col = c
            break
    if col is None:
        return None
    try:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        return float(vals.sum()) if not vals.empty else None
    except Exception:
        return None

def trade_snapshot(reporter: int, year: int = 2022) -> Dict[str, Optional[float]]:
    """Snapshot: imports & exports to world (partner=0)."""
    imp = total_trade_value_usd(comtrade_query(reporter, partner=0, year=year, trade_flow="1"))
    exp = total_trade_value_usd(comtrade_query(reporter, partner=0, year=year, trade_flow="2"))
    tot = (imp + exp) if (imp is not None and exp is not None) else None
    return {"imports_usd": imp, "exports_usd": exp, "total_trade_usd": tot}

def wto_is_configured() -> bool:
    return bool(os.getenv("WTO_SUBSCRIPTION_KEY", "").strip())
