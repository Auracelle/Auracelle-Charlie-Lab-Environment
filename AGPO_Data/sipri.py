"""
AGPO Data Package - SIPRI Military Expenditure Integration
Note: SIPRI requires manual CSV download. This module processes the data.
"""
import pandas as pd
import streamlit as st
import io

def parse_sipri_csv(uploaded_file):
    """
    Parse SIPRI military expenditure CSV
    Download from: https://www.sipri.org/databases/milex
    """
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        return df
    except Exception as e:
        st.error(f"SIPRI CSV parsing error: {e}")
        return pd.DataFrame()

def get_military_expenditure_by_country(df, country_name, year=2023):
    """Extract military expenditure for specific country and year"""
    try:
        if 'Country' in df.columns and str(year) in df.columns:
            country_data = df[df['Country'] == country_name]
            if not country_data.empty:
                value = country_data[str(year)].iloc[0]
                return value
        return None
    except:
        return None

def get_top_military_spenders(df, year=2023, top_n=10):
    """Get top N military spenders for a given year"""
    try:
        if str(year) in df.columns:
            top = df.nlargest(top_n, str(year))[['Country', str(year)]]
            return top
        return pd.DataFrame()
    except:
        return pd.DataFrame()
