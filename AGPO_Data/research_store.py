from __future__ import annotations
import sqlite3, time, json
from typing import Any, Dict

DB_PATH = "auracelle_research.db"

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA foreign_keys=ON;")
    return c

def init_db() -> None:
    con = _conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at INTEGER NOT NULL,
        scenario TEXT,
        condition_tag TEXT,
        started_at INTEGER,
        ended_at INTEGER,
        completed INTEGER DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        participant_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        alias TEXT,
        consent INTEGER DEFAULT 0,
        gender TEXT,
        sector TEXT,
        military_status TEXT,
        role_function TEXT,
        years_experience TEXT,
        wargame_experience TEXT,
        ai_gov_familiarity TEXT,
        age_band TEXT,
        education_band TEXT,
        region TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        participant_id TEXT,
        t INTEGER NOT NULL,
        round_num INTEGER,
        policy TEXT,
        action TEXT,
        notes TEXT,
        state_json TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS outcomes (
        session_id TEXT PRIMARY KEY,
        t INTEGER NOT NULL,
        trust REAL,
        compliance REAL,
        alignment REAL,
        resilience REAL,
        unintended_json TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    """)
    con.commit()
    con.close()

def upsert_session(session_id: str, scenario: str | None = None, condition_tag: str | None = None) -> None:
    con = _conn()
    t = int(time.time())
    con.execute("""
      INSERT INTO sessions(session_id, created_at, scenario, condition_tag)
      VALUES(?,?,?,?)
      ON CONFLICT(session_id) DO UPDATE SET scenario=excluded.scenario, condition_tag=excluded.condition_tag
    """, (session_id, t, scenario, condition_tag))
    con.commit()
    con.close()

def upsert_participant(participant_id: str, session_id: str, profile: Dict[str, Any]) -> None:
    con = _conn()
    t = int(time.time())
    con.execute("""
      INSERT INTO participants(participant_id, session_id, created_at, alias, consent, gender, sector, military_status,
                               role_function, years_experience, wargame_experience, ai_gov_familiarity,
                               age_band, education_band, region)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(participant_id) DO UPDATE SET
        alias=excluded.alias, consent=excluded.consent, gender=excluded.gender, sector=excluded.sector,
        military_status=excluded.military_status, role_function=excluded.role_function,
        years_experience=excluded.years_experience, wargame_experience=excluded.wargame_experience,
        ai_gov_familiarity=excluded.ai_gov_familiarity, age_band=excluded.age_band,
        education_band=excluded.education_band, region=excluded.region
    """, (
        participant_id, session_id, t,
        profile.get("alias"), int(bool(profile.get("consent"))), profile.get("gender"), profile.get("sector"), profile.get("military_status"),
        profile.get("role_function"), profile.get("years_experience"), profile.get("wargame_experience"), profile.get("ai_gov_familiarity"),
        profile.get("age_band"), profile.get("education_band"), profile.get("region")
    ))
    con.commit()
    con.close()

def log_move(session_id: str, participant_id: str | None, round_num: int | None,
             policy: str | None, action: str | None, notes: str | None,
             state: Dict[str, Any] | None = None) -> None:
    con = _conn()
    t = int(time.time())
    con.execute("""
      INSERT INTO moves(session_id, participant_id, t, round_num, policy, action, notes, state_json)
      VALUES(?,?,?,?,?,?,?,?)
    """, (session_id, participant_id, t, round_num, policy, action, notes, json.dumps(state or {})))
    con.commit()
    con.close()

def set_outcomes(session_id: str, trust: float, compliance: float, alignment: float, resilience: float,
                 unintended: Dict[str, Any] | None = None) -> None:
    con = _conn()
    t = int(time.time())
    con.execute("""
      INSERT INTO outcomes(session_id, t, trust, compliance, alignment, resilience, unintended_json)
      VALUES(?,?,?,?,?,?,?)
      ON CONFLICT(session_id) DO UPDATE SET
        t=excluded.t, trust=excluded.trust, compliance=excluded.compliance, alignment=excluded.alignment,
        resilience=excluded.resilience, unintended_json=excluded.unintended_json
    """, (session_id, t, trust, compliance, alignment, resilience, json.dumps(unintended or {})))
    con.commit()
    con.close()
