"""Actor mapping helpers for Auracelle Charlie (ISO3, UN M49, Comtrade codes).

Why:
- Charlie's UI uses "Actors" (Dubai, UK, NATO, etc.)
- Different external datasets key countries differently:
  * ISO3 alpha codes (World Bank, IMF DataMapper)
  * UN M49 numeric codes (UN SDG API)
  * UN Comtrade numeric reporter/partner codes (commonly aligned with M49)

Design principle:
- Provide thin, explicit mappings for Charlie's canonical actor list.
- Degrade gracefully for non-state actors (e.g., NATO).
"""

from __future__ import annotations
from typing import Optional, Dict

# --- ISO3 (alpha-3) codes ---
ACTOR_TO_ISO3: Dict[str, str] = {
    "Dubai": "ARE",   # Dubai -> UAE
    "UK": "GBR",
    "US": "USA",
    "Japan": "JPN",
    "China": "CHN",
    "Brazil": "BRA",
    "India": "IND",
    # New actors
    "Israel": "ISR",
    "Paraguay": "PRY",
    "Belgium": "BEL",
    "Denmark": "DNK",
    "Ukraine": "UKR",
    "Serbia": "SRB",
    "Argentina": "ARG",
    "Norway": "NOR",
    "Switzerland": "CHE",
    "Poland": "POL",
    # Regional / alliance entities (no single ISO3)
    "NATO": "NATO",
    "Global South": None,
}

# --- UN M49 numeric codes (used by UNSD SDG API) ---
# Source: UN M49 standard (numeric geo area codes). Keep tight for Charlie's list.
ACTOR_TO_M49: Dict[str, int] = {
    "Dubai": 784,   # United Arab Emirates
    "UK": 826,      # United Kingdom
    "US": 840,      # United States of America (note: UN SDG API often uses 840)
    "Japan": 392,
    "China": 156,
    "Brazil": 76,
    "India": 356,
    # New actors
    "Israel": 376,
    "Paraguay": 600,
    "Belgium": 56,
    "Denmark": 208,
    "Ukraine": 804,
    "Serbia": 688,
    "Argentina": 32,
    "Norway": 578,
    "Switzerland": 756,
    "Poland": 616,
}

# --- UN Comtrade reporter/partner numeric codes ---
# Classic Comtrade API examples use numeric codes (e.g., Germany=276). For Charlie list,
# these align with the same UN M49 numeric codes above.
ACTOR_TO_COMTRADE: Dict[str, int] = dict(ACTOR_TO_M49)

def actor_to_iso3(actor: str) -> Optional[str]:
    return ACTOR_TO_ISO3.get(actor)

def actor_to_m49(actor: str) -> Optional[int]:
    return ACTOR_TO_M49.get(actor)

def actor_to_comtrade(actor: str) -> Optional[int]:
    return ACTOR_TO_COMTRADE.get(actor)
