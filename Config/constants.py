"""
Auracelle Charlie — Application constants.

Secret values (LOGIN_PASSWORD, API keys) should be set via environment
variables or st.secrets — never committed to git.  The values here are
safe development defaults only.
"""
import os

# ── Application identity ──────────────────────────────────────────────────────
APP_TITLE = (
    "Auracelle Charlie 3 — War Gaming Stress-Testing "
    "Policy Governance Research Simulation/Prototype"
)
APP_ICON = "🔐"
APP_VERSION = "3.0.0-phase0"

# ── Auth ──────────────────────────────────────────────────────────────────────
# Override via environment variable or .streamlit/secrets.toml
# NEVER commit a real password to source control.
LOGIN_PASSWORD: str = os.environ.get("CHARLIE_LOGIN_PASSWORD", "charlie2025")

# ── Backend ───────────────────────────────────────────────────────────────────
FASTAPI_BASE_URL: str = os.environ.get("CHARLIE_FASTAPI_URL", "http://127.0.0.1:8000")

# ── Research database ─────────────────────────────────────────────────────────
DB_PATH: str = os.environ.get("CHARLIE_DB_PATH", "data/auracelle_research.db")

# ── World Bank cache TTL (seconds) ────────────────────────────────────────────
WB_CACHE_TTL: int = 3600

# ── Simulation defaults ───────────────────────────────────────────────────────
DEFAULT_EPISODE_LENGTH: int = 5
DEFAULT_SHOCK_SIGMA: float = 0.02

# ── Page names (used for st.switch_page) ──────────────────────────────────────
PAGE_SESSION_SETUP = "pages/01_Session_Setup.py"
PAGE_SIMULATION = "pages/02_Simulation.py"
PAGE_POLICY_STRESS = "pages/03_Policy_Stress_Testing.py"
PAGE_MISSION_CONSOLE = "pages/04_Mission_Console.py"
PAGE_REAL_WORLD = "pages/05_Real_World_Data_Metrics.py"
PAGE_ADMIN = "pages/06_Admin_Dashboard.py"
