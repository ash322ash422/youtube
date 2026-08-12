# job_store.py
"""
Tracks the status of every pipeline run in a SQLite database, one row per
run, keyed by job_id (a UUID generated per run - see new_job_id()).

Keyed by job_id rather than blob_name so that re-processing the same
filename (or two different users uploading a file with the same name)
never overwrites another run's status - the old version keyed a single
JSON file by blob_name, which meant exactly that collision.
"""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                blob_name TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                failed_stage TEXT,
                download_url TEXT,
                token_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def new_job_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def update_job(job_id: str, **fields: Any) -> dict:
    """
    Upsert: creates the row the first time a job_id is seen (using
    `fields` for the initial values, defaulting status to PENDING),
    otherwise merges `fields` into the existing row. Mirrors the old
    JSON-backed job_store's "create or merge" behaviour.
    """
    init_db()
    now = _now()
    conn = _connect()
    try:
        existing = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

        if existing is None:
            row = {
                "job_id": job_id,
                "blob_name": fields.get("blob_name", ""),
                "status": fields.get("status", "PENDING"),
                "error": fields.get("error"),
                "failed_stage": fields.get("failed_stage"),
                "download_url": fields.get("download_url"),
                "token_count": fields.get("token_count", 0),
                "created_at": now,
                "updated_at": now,
                "completed_at": fields.get("completed_at"),
            }
            conn.execute(
                """
                INSERT INTO jobs
                    (job_id, blob_name, status, error, failed_stage, download_url,
                     token_count, created_at, updated_at, completed_at)
                VALUES
                    (:job_id, :blob_name, :status, :error, :failed_stage, :download_url,
                     :token_count, :created_at, :updated_at, :completed_at)
                """,
                row,
            )
        else:
            merged = dict(existing)
            merged.update(fields)
            merged["updated_at"] = now
            conn.execute(
                """
                UPDATE jobs SET
                    blob_name = :blob_name, status = :status, error = :error,
                    failed_stage = :failed_stage, download_url = :download_url,
                    token_count = :token_count, updated_at = :updated_at,
                    completed_at = :completed_at
                WHERE job_id = :job_id
                """,
                merged,
            )

        conn.commit()
        return dict(conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone())
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[dict]:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def all_jobs() -> list[dict]:
    """
    Every job, most recently created first. created_at only has
    second-level resolution, so rowid (insertion order) breaks ties
    between jobs created within the same second.
    """
    init_db()
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC, rowid DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def total_token_usage() -> int:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT COALESCE(SUM(token_count), 0) AS total FROM jobs").fetchone()
        return row["total"]
    finally:
        conn.close()
