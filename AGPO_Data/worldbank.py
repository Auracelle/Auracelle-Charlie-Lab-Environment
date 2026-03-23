"""AGPO Data Package - World Bank API Integration (robust)

Fetches real-world economic and development indicators for Auracelle Charlie.

Notes:
- Uses wbgapi (World Bank API client).
- Degrades gracefully if an economy code isn't supported.
"""

from __future__ import annotations

from typing import List, Optional
import pandas as pd
import streamlit as st
import wbgapi as wb

def _normalize_year_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize year columns from wbgapi (e.g., 'YR2000' -> '2000')."""
    cols = []
    for c in df.columns:
        s = str(c)
        if s.startswith("YR") and s[2:].isdigit():
            s = s[2:]
        cols.append(s)
    df.columns = cols
    return df

def _pick_country_col(df: pd.DataFrame) -> str:
    for c in ["Country", "country", "Economy", "economy", "name"]:
        if c in df.columns:
            return c
    non_year = [c for c in df.columns if not str(c).isdigit()]
    return non_year[0] if non_year else df.columns[0]

@st.cache_data(ttl=3600)
def get_world_bank_indicator(
    indicator_code: str,
    country_codes: List[str],
    start_year: int = 2015,
    end_year: int = 2024,
) -> pd.DataFrame:
    """Return long-form DataFrame with columns: Country, Year, Value, Indicator, ISO3"""
    try:
        years = list(range(int(start_year), int(end_year) + 1))

        df = wb.data.DataFrame(
            indicator_code,
            economy=country_codes,
            time=years,
            labels=True
        )

        if df is None or len(df) == 0:
            return pd.DataFrame()

        df = df.reset_index()
        country_col = _pick_country_col(df)
        df = _normalize_year_cols(df)

        year_cols = [c for c in df.columns if str(c).isdigit() and len(str(c)) == 4]
        if not year_cols:
            return pd.DataFrame()

        long_df = df.melt(
            id_vars=[country_col],
            value_vars=year_cols,
            var_name="Year",
            value_name="Value",
        ).rename(columns={country_col: "Country"})

        # Attach ISO3 if present
        if "economy" in df.columns:
            mapping = df[[country_col, "economy"]].drop_duplicates().rename(columns={country_col: "Country", "economy": "ISO3"})
            long_df = long_df.merge(mapping, on="Country", how="left")
        else:
            long_df["ISO3"] = None

        long_df["Indicator"] = indicator_code
        long_df["Year"] = pd.to_numeric(long_df["Year"], errors="coerce").astype("Int64")
        long_df["Value"] = pd.to_numeric(long_df["Value"], errors="coerce")
        return long_df.dropna(subset=["Year"])
    except Exception as e:
        st.warning(f"World Bank API error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_many_indicators(
    indicator_codes: List[str] | dict,
    country_codes: List[str],
    start_year: int = 2015,
    end_year: int = 2024,
) -> pd.DataFrame:
    # Accept either a list of WB indicator codes or a {label: code} dict.
    if isinstance(indicator_codes, dict):
        indicator_codes = list(indicator_codes.values())
    frames = []
    for code in indicator_codes:
        df = get_world_bank_indicator(code, country_codes, start_year, end_year)
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def latest_value(df: pd.DataFrame, iso3: str, indicator_code: str) -> Optional[float]:
    try:
        sub = df[(df["ISO3"] == iso3) & (df["Indicator"] == indicator_code)].dropna(subset=["Value"])
        if sub.empty:
            return None
        row = sub.sort_values("Year", ascending=False).iloc[0]
        return float(row["Value"])
    except Exception:
        return None

def get_latest_gdp(country_code: str) -> Optional[float]:
    """Backwards-compatible helper: latest GDP in trillions USD."""
    df = get_world_bank_indicator("NY.GDP.MKTP.CD", [country_code], start_year=2000, end_year=2025)
    val = latest_value(df, df["ISO3"].iloc[0] if not df.empty else country_code, "NY.GDP.MKTP.CD")
    return (val / 1e12) if val is not None else None

def get_latest_military_expenditure(country_code: str) -> Optional[float]:
    """Backwards-compatible helper: latest military expenditure (% of GDP)."""
    df = get_world_bank_indicator("MS.MIL.XPND.GD.ZS", [country_code], start_year=2000, end_year=2025)
    val = latest_value(df, df["ISO3"].iloc[0] if not df.empty else country_code, "MS.MIL.XPND.GD.ZS")
    return val
def get_internet_penetration(country_code: str) -> Optional[float]:
    """Backwards-compatible helper: latest internet users (% of population)."""
    df = get_world_bank_indicator("IT.NET.USER.ZS", [country_code], start_year=2000, end_year=2025)
    if df.empty:
        return None
    iso = df["ISO3"].dropna().iloc[0] if "ISO3" in df.columns and df["ISO3"].notna().any() else country_code
    return latest_value(df, iso, "IT.NET.USER.ZS")
