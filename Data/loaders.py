"""
data/loaders.py — External data source wrappers.

Consolidates World Bank, Export Controls, IMF, UN SDG, and Trade data
fetching.  All functions are wrapped in try/except and return empty
DataFrames / None on failure so pages degrade gracefully.

Streamlit @st.cache_data decorators are applied here; pages simply import
and call these functions.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st

from config.constants import WB_CACHE_TTL

# ── World Bank ────────────────────────────────────────────────────────────────

WB_INDICATORS = {
    "GDP (current US$)":             "NY.GDP.MKTP.CD",
    "Military Expenditure (% GDP)":  "MS.MIL.XPND.GD.ZS",
    "Internet Users (% population)": "IT.NET.USER.ZS",
    "Trade (% of GDP)":              "NE.TRD.GNFS.ZS",
    "Inflation (CPI %)":             "FP.CPI.TOTL.ZG",
    "R&D Expenditure (% GDP)":       "GB.XPD.RSDV.GD.ZS",
}


@st.cache_data(ttl=WB_CACHE_TTL)
def get_world_bank_indicator(
    indicator_code: str,
    country_codes: list[str],
    start_year: int = 2015,
    end_year: int = 2024,
) -> pd.DataFrame:
    """Fetch a World Bank indicator for a list of ISO3 country codes."""
    try:
        import wbgapi as wb
        data = wb.data.DataFrame(
            indicator_code,
            country_codes,
            time=range(start_year, end_year + 1),
            labels=True,
        )
        data_reset = data.reset_index()
        data_melted = data_reset.melt(
            id_vars=["Country"], var_name="Year", value_name="Value"
        )
        data_melted["Indicator"] = indicator_code
        return data_melted
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=WB_CACHE_TTL)
def get_many_indicators(
    country_codes: list[str],
    start_year: int = 2015,
    end_year: int = 2024,
) -> dict[str, pd.DataFrame]:
    """Fetch all WB_INDICATORS for a list of countries. Returns {indicator_label: df}."""
    result: dict[str, pd.DataFrame] = {}
    for label, code in WB_INDICATORS.items():
        result[label] = get_world_bank_indicator(code, country_codes, start_year, end_year)
    return result


@st.cache_data(ttl=WB_CACHE_TTL)
def latest_value(
    indicator_code: str,
    iso3: str,
) -> float | None:
    """Return the most recent non-null value for an indicator / country pair."""
    df = get_world_bank_indicator(indicator_code, [iso3])
    if df.empty:
        return None
    col = "Value"
    valid = df[df[col].notna()].sort_values("Year", ascending=False)
    if valid.empty:
        return None
    return float(valid.iloc[0][col])


def get_latest_gdp(iso3: str) -> float | None:
    """GDP in current USD for given ISO3 country."""
    raw = latest_value("NY.GDP.MKTP.CD", iso3)
    if raw is None:
        return None
    return round(raw / 1e12, 3)  # convert to USD trillions


def get_latest_military_expenditure(iso3: str) -> float | None:
    return latest_value("MS.MIL.XPND.GD.ZS", iso3)


def get_internet_penetration(iso3: str) -> float | None:
    return latest_value("IT.NET.USER.ZS", iso3)


# ── US Export Controls / Consolidated Screening List ─────────────────────────

@st.cache_data(ttl=86400)
def fetch_consolidated_screening_list() -> pd.DataFrame:
    """Fetch CSL from trade.gov (returns empty DF if API unavailable/auth required)."""
    url = "https://api.trade.gov/consolidated_screening_list/search"
    try:
        resp = requests.get(url, params={"size": 100, "offset": 0}, timeout=10)
        if resp.status_code == 403 or not resp.text.strip():
            return pd.DataFrame()
        resp.raise_for_status()
        results = resp.json().get("results", [])
        records = [
            {
                "name":     item.get("name", "N/A"),
                "country":  (item.get("addresses") or [{}])[0].get("country", "N/A"),
                "source":   item.get("source", "N/A"),
                "type":     item.get("type", "N/A"),
                "programs": ", ".join(item.get("programs", [])),
                "remarks":  item.get("remarks", ""),
            }
            for item in results
        ]
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()


def get_sanctioned_countries() -> dict[str, int]:
    """Return {country: entity_count} dict from CSL data."""
    df = fetch_consolidated_screening_list()
    if df.empty:
        return {}
    return df["country"].value_counts().to_dict()


# ── IMF WEO (lightweight scrape) ──────────────────────────────────────────────

@st.cache_data(ttl=WB_CACHE_TTL)
def macro_snapshot(iso3: str) -> dict[str, Any]:
    """
    Return a macro snapshot dict for a country.
    Uses World Bank proxies for IMF-style indicators where the
    IMF WEO API requires authentication.
    """
    gdp = get_latest_gdp(iso3)
    return {
        "GDP_USD_trillions": gdp,
        "source": "World Bank (GDP proxy)",
        "note": "IMF WEO direct API requires authentication; WB used as proxy.",
    }


# ── UN SDG ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=WB_CACHE_TTL)
def social_snapshot(iso3: str) -> dict[str, Any]:
    """Return available SDG-adjacent indicators for a country."""
    internet = get_internet_penetration(iso3)
    return {
        "internet_penetration_pct": internet,
        "source": "World Bank",
    }


# ── Trade (UN Comtrade proxy) ─────────────────────────────────────────────────

@st.cache_data(ttl=WB_CACHE_TTL)
def trade_snapshot(iso3: str, year: int = 2022) -> dict[str, Any]:
    """
    Return trade-as-pct-GDP for a country (World Bank proxy for Comtrade).
    Full Comtrade API requires a subscription key.
    """
    trade_pct = latest_value("NE.TRD.GNFS.ZS", iso3)
    return {
        "trade_pct_gdp": trade_pct,
        "year": year,
        "source": "World Bank (Comtrade proxy)",
    }


# ── Actor map helpers ─────────────────────────────────────────────────────────

def actor_to_iso3(actor_name: str) -> str | None:
    """Resolve actor display name to ISO3 via config/actors.yaml."""
    try:
        from engine.actors import get_iso3_map
        return get_iso3_map().get(actor_name)
    except Exception:
        return None
