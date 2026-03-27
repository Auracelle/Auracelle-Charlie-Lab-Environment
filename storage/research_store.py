"""
storage/research_store.py — SQLite research database.

Schema: sessions → participants → moves → outcomes
DB path is controlled by config.constants.DB_PATH (env-overridable).
All functions are safe to call from Streamlit's threaded runtime.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def _db_path() -> str:
    # Import here to avoid circular imports at module load time
    from config.constants import DB_PATH
    # Ensure parent directory exists
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_db_path(), check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA foreign_keys=ON;")
    return c


def init_db() -> None:
    con = _conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id   TEXT PRIMARY KEY,
        created_at   INTEGER NOT NULL,
        scenario     TEXT,
        condition_tag TEXT,
        started_at   INTEGER,
        ended_at     INTEGER,
        completed    INTEGER DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        participant_id   TEXT PRIMARY KEY,
        session_id       TEXT NOT NULL,
        created_at       INTEGER NOT NULL,
        alias            TEXT,
        consent          INTEGER DEFAULT 0,
        gender           TEXT,
        sector           TEXT,
        military_status  TEXT,
        role_function    TEXT,
        years_experience TEXT,
        wargame_experience TEXT,
        ai_gov_familiarity TEXT,
        age_band         TEXT,
        education_band   TEXT,
        region           TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS moves (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id     TEXT NOT NULL,
        participant_id TEXT,
        t              INTEGER NOT NULL,
        round_num      INTEGER,
        policy         TEXT,
        action         TEXT,
        notes          TEXT,
        state_json     TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS outcomes (
        session_id     TEXT PRIMARY KEY,
        t              INTEGER NOT NULL,
        trust          REAL,
        compliance     REAL,
        alignment      REAL,
        resilience     REAL,
        unintended_json TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    con.commit()
    con.close()


def upsert_session(
    session_id: str,
    scenario: str | None = None,
    condition_tag: str | None = None,
) -> None:
    con = _conn()
    t = int(time.time())
    con.execute(
        """
        INSERT INTO sessions(session_id, created_at, scenario, condition_tag)
        VALUES(?,?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET
            scenario=excluded.scenario,
            condition_tag=excluded.condition_tag
        """,
        (session_id, t, scenario, condition_tag),
    )
    con.commit()
    con.close()


def upsert_participant(
    participant_id: str,
    session_id: str,
    profile: dict[str, Any],
) -> None:
    con = _conn()
    t = int(time.time())
    con.execute(
        """
        INSERT INTO participants(
            participant_id, session_id, created_at, alias, consent, gender, sector,
            military_status, role_function, years_experience, wargame_experience,
            ai_gov_familiarity, age_band, education_band, region
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(participant_id) DO UPDATE SET
            alias=excluded.alias, consent=excluded.consent, gender=excluded.gender,
            sector=excluded.sector, military_status=excluded.military_status,
            role_function=excluded.role_function, years_experience=excluded.years_experience,
            wargame_experience=excluded.wargame_experience,
            ai_gov_familiarity=excluded.ai_gov_familiarity, age_band=excluded.age_band,
            education_band=excluded.education_band, region=excluded.region
        """,
        (
            participant_id, session_id, t,
            profile.get("alias"),
            int(bool(profile.get("consent"))),
            profile.get("gender"),
            profile.get("sector"),
            profile.get("military_status"),
            profile.get("role_function"),
            profile.get("years_experience"),
            profile.get("wargame_experience"),
            profile.get("ai_gov_familiarity"),
            profile.get("age_band"),
            profile.get("education_band"),
            profile.get("region"),
        ),
    )
    con.commit()
    con.close()


def log_move(
    session_id: str,
    participant_id: str | None,
    round_num: int | None,
    policy: str | None,
    action: str | None,
    notes: str | None = None,
    state_json: str | None = None,
) -> None:
    con = _conn()
    t = int(time.time())
    con.execute(
        """
        INSERT INTO moves(session_id, participant_id, t, round_num, policy, action, notes, state_json)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (session_id, participant_id, t, round_num, policy, action, notes, state_json or "{}"),
    )
    con.commit()
    con.close()


def set_outcomes(
    session_id: str,
    trust: float,
    compliance: float,
    alignment: float,
    resilience: float,
    unintended: dict[str, Any] | None = None,
) -> None:
    con = _conn()
    t = int(time.time())
    con.execute(
        """
        INSERT INTO outcomes(session_id, t, trust, compliance, alignment, resilience, unintended_json)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET
            t=excluded.t, trust=excluded.trust, compliance=excluded.compliance,
            alignment=excluded.alignment, resilience=excluded.resilience,
            unintended_json=excluded.unintended_json
        """,
        (session_id, t, trust, compliance, alignment, resilience, json.dumps(unintended or {})),
    )
    con.commit()
    con.close()


def fetch_session_moves(session_id: str) -> list[dict]:
    """Return all moves for a session, ordered by time."""
    con = _conn()
    cur = con.execute(
        "SELECT * FROM moves WHERE session_id=? ORDER BY t ASC",
        (session_id,),
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    con.close()
    return rows


def fetch_all_sessions() -> list[dict]:
    """Return all sessions (for admin dashboard)."""
    con = _conn()
    cur = con.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    con.close()
    return rows


def fetch_all_participants() -> list[dict]:
    """Return all participants (for admin dashboard)."""
    con = _conn()
    cur = con.execute("SELECT * FROM participants ORDER BY created_at DESC")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    con.close()
    return rows
