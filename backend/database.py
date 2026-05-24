"""
SQLite database manager untuk menyimpan job metadata scraping.
DB disimpan di: backend/scraper_jobs.db
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


DB_PATH = Path(__file__).parent / "scraper_jobs.db"
logger  = logging.getLogger("backend.database")


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scrape_jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    platform     TEXT NOT NULL,
    keyword      TEXT,
    states       TEXT,          -- JSON list
    start_url    TEXT,
    pages        INTEGER,
    status       TEXT NOT NULL DEFAULT 'queued',
    progress     INTEGER DEFAULT 0,
    total_found  INTEGER DEFAULT 0,
    output_file  TEXT,          -- full path
    file_name    TEXT,          -- basename saja
    error        TEXT,
    started_at   TEXT,
    finished_at  TEXT,
    created_at   TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # bisa akses kolom by name
    return conn


def init_db():
    """Buat tabel jika belum ada. Dipanggil saat startup FastAPI."""
    with get_conn() as conn:
        conn.execute(CREATE_TABLE_SQL)
        try:
            conn.execute("ALTER TABLE scrape_jobs ADD COLUMN start_url TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE scrape_jobs ADD COLUMN pages INTEGER")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    logger.info(f"SQLite DB ready at {DB_PATH}")


# ── CRUD ──────────────────────────────────────────────────────────────────────

def insert_job(
    platform: str,
    start_url: str,
    pages: int,
) -> int:
    """Insert job baru, return integer id yang di-generate DB."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scrape_jobs
                (platform, start_url, pages, status, created_at)
            VALUES (?, ?, ?, 'queued', ?)
            """,
            (platform, start_url, pages,
             datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid  # integer auto-increment id


def update_job(job_id: int, **fields):
    """
    Update kolom tertentu by integer id. Contoh:
        update_job(1, status="running", started_at="...")
        update_job(1, status="done", total_found=132, file_name="...")
    """
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values     = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE scrape_jobs SET {set_clause} WHERE id = ?",
            values,
        )
        conn.commit()


def get_job(job_id: int) -> Optional[dict]:
    """Ambil satu job by integer id. Return dict atau None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    if row:
        d = dict(row)
        if "states" in d and d["states"]:
            try:
                d["states"] = json.loads(d["states"])
            except:
                d["states"] = []
        return d
    return None


def list_all_jobs() -> list[dict]:
    """Ambil semua job, urut terbaru duluan."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scrape_jobs ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if "states" in d and d["states"]:
            try:
                d["states"] = json.loads(d["states"])
            except:
                d["states"] = []
        result.append(d)
    return result

def get_completed_jobs_for_platform(platform: str) -> list[dict]:
    """Fetch completed jobs for a platform to read their CSVs for skipping existing URLs."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT output_file FROM scrape_jobs WHERE platform = ? AND output_file IS NOT NULL", (platform,)
        ).fetchall()
    return [dict(r) for r in rows]

def update_job_status(job_id: int, status: str, error: str = None):
    """Update status job di DB."""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE scrape_jobs
            SET status = ?, error = ?, finished_at = ?
            WHERE id = ?
            """,
            (status, error, datetime.now().isoformat(), job_id),
        )
        conn.commit()