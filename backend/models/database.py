"""SQLite database setup using aiosqlite for async access."""

import aiosqlite
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import settings

DB_PATH = settings.db_path


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                job_description_text TEXT,
                job_requirements_json TEXT,
                status TEXT DEFAULT 'created'
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                parsed_resume_json TEXT,
                match_analysis_json TEXT,
                overall_score INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_candidates_session
                ON candidates(session_id);

            CREATE INDEX IF NOT EXISTS idx_candidates_score
                ON candidates(session_id, overall_score DESC);
        """)
        await db.commit()
    finally:
        await db.close()


# ─── Session Operations ──────────────────────────────────────────────────────


async def create_session() -> str:
    """Create a new analysis session. Returns the session ID."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, now),
        )
        await db.commit()
        return session_id
    finally:
        await db.close()


async def get_session(session_id: str) -> dict | None:
    """Get a session by ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        await db.close()


async def update_session_jd(session_id: str, jd_text: str, jd_requirements_json: str | None = None):
    """Update a session with job description text and optionally parsed requirements."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE sessions 
               SET job_description_text = ?, job_requirements_json = ?
               WHERE id = ?""",
            (jd_text, jd_requirements_json, session_id),
        )
        await db.commit()
    finally:
        await db.close()


async def update_session_status(session_id: str, status: str):
    """Update session status."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE sessions SET status = ? WHERE id = ?",
            (status, session_id),
        )
        await db.commit()
    finally:
        await db.close()


# ─── Candidate Operations ────────────────────────────────────────────────────


async def create_candidate(session_id: str, filename: str, raw_text: str) -> str:
    """Create a new candidate record. Returns the candidate ID."""
    candidate_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO candidates (id, session_id, filename, raw_text, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (candidate_id, session_id, filename, raw_text, now),
        )
        await db.commit()
        return candidate_id
    finally:
        await db.close()


async def update_candidate_parsed(candidate_id: str, parsed_resume_json: str):
    """Update candidate with parsed resume data."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE candidates SET parsed_resume_json = ? WHERE id = ?",
            (parsed_resume_json, candidate_id),
        )
        await db.commit()
    finally:
        await db.close()


async def update_candidate_analysis(
    candidate_id: str, match_analysis_json: str, overall_score: int
):
    """Update candidate with match analysis results."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE candidates 
               SET match_analysis_json = ?, overall_score = ?
               WHERE id = ?""",
            (match_analysis_json, overall_score, candidate_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_candidates_by_session(session_id: str) -> list[dict]:
    """Get all candidates for a session, ordered by score descending."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM candidates 
               WHERE session_id = ? 
               ORDER BY overall_score DESC NULLS LAST""",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_candidate(candidate_id: str) -> dict | None:
    """Get a single candidate by ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        await db.close()


async def get_session_candidate_count(session_id: str) -> int:
    """Get the number of candidates in a session."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM candidates WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"]
    finally:
        await db.close()


async def delete_session(session_id: str):
    """Delete a session and all its candidates."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    finally:
        await db.close()
