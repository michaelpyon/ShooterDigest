"""Postgres connection pool and schema for ShooterDigest.

All database access goes through this module.
Requires DATABASE_URL in the environment (Postgres connection string).
"""

from __future__ import annotations

import json
import logging
import os
import threading

import psycopg2
import psycopg2.extras
import psycopg2.pool

log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                if not DATABASE_URL:
                    raise RuntimeError(
                        "DATABASE_URL is not set. "
                        "ShooterDigest requires a Postgres connection string."
                    )
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=5,
                    dsn=DATABASE_URL,
                )
    return _pool


class _ConnCtx:
    """Context manager that checks out and returns a pooled connection."""

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = _get_pool().getconn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
            _get_pool().putconn(self.conn)
            self.conn = None
        return False


def get_conn():
    """Return a context manager for a pooled Postgres connection."""
    return _ConnCtx()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_key     TEXT PRIMARY KEY,
    pipeline    TEXT NOT NULL,
    run_date    TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_date
ON pipeline_runs(pipeline, run_date DESC);

CREATE TABLE IF NOT EXISTS http_cache (
    cache_key    TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    url          TEXT NOT NULL,
    status_code  INTEGER NOT NULL,
    headers_json TEXT NOT NULL,
    body         TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fetched_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_runs (
    id           SERIAL PRIMARY KEY,
    source       TEXT NOT NULL,
    url          TEXT NOT NULL,
    cache_hit    INTEGER NOT NULL,
    status_code  INTEGER NOT NULL,
    content_hash TEXT,
    fetched_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS digest_html (
    run_date    TEXT PRIMARY KEY,
    html        TEXT NOT NULL,
    teaser      TEXT NOT NULL DEFAULT '',
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_digest_html_date
ON digest_html(run_date DESC);
"""


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
    log.info("ShooterDigest DB schema initialized")


# ---------------------------------------------------------------------------
# Pipeline runs (snapshot storage)
# ---------------------------------------------------------------------------

def upsert_pipeline_run(
    run_key: str,
    pipeline: str,
    run_date: str,
    payload_json: str,
    content_hash: str,
    now: int,
    *,
    overwrite: bool = True,
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if overwrite:
                cur.execute(
                    """
                    INSERT INTO pipeline_runs
                        (run_key, pipeline, run_date, payload_json, content_hash, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_key) DO UPDATE SET
                        payload_json = EXCLUDED.payload_json,
                        content_hash = EXCLUDED.content_hash,
                        updated_at   = EXCLUDED.updated_at
                    """,
                    (run_key, pipeline, run_date, payload_json, content_hash, now, now),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO pipeline_runs
                        (run_key, pipeline, run_date, payload_json, content_hash, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_key) DO NOTHING
                    """,
                    (run_key, pipeline, run_date, payload_json, content_hash, now, now),
                )


def load_pipeline_run(
    *,
    run_key: str | None = None,
    pipeline: str | None = None,
    run_date: str | None = None,
) -> str | None:
    """Return payload_json for a specific run, or None."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if run_key:
                cur.execute(
                    "SELECT payload_json FROM pipeline_runs WHERE run_key = %s",
                    (run_key,),
                )
            elif pipeline and run_date:
                cur.execute(
                    """
                    SELECT payload_json FROM pipeline_runs
                    WHERE pipeline = %s AND run_date = %s
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (pipeline, run_date),
                )
            else:
                return None
            row = cur.fetchone()
    return row[0] if row else None


def load_latest_pipeline_run(*, pipeline: str) -> str | None:
    """Return payload_json for the most recent run of a pipeline."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json FROM pipeline_runs
                WHERE pipeline = %s
                ORDER BY run_date DESC, updated_at DESC
                LIMIT 1
                """,
                (pipeline,),
            )
            row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# HTTP cache
# ---------------------------------------------------------------------------

def read_http_cache(cache_key: str) -> tuple | None:
    """Return (status_code, headers_json, body, content_hash, fetched_at) or None."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status_code, headers_json, body, content_hash, fetched_at
                FROM http_cache WHERE cache_key = %s
                """,
                (cache_key,),
            )
            return cur.fetchone()


def write_http_cache(
    cache_key: str,
    source: str,
    url: str,
    status_code: int,
    headers_json: str,
    body: str,
    content_hash: str,
    fetched_at: int,
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO http_cache
                    (cache_key, source, url, status_code, headers_json, body, content_hash, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                    status_code  = EXCLUDED.status_code,
                    headers_json = EXCLUDED.headers_json,
                    body         = EXCLUDED.body,
                    content_hash = EXCLUDED.content_hash,
                    fetched_at   = EXCLUDED.fetched_at
                """,
                (cache_key, source, url, status_code, headers_json, body, content_hash, fetched_at),
            )


def record_fetch_run(
    source: str, url: str, cache_hit: bool, status_code: int, content_hash: str | None
) -> None:
    import time

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fetch_runs (source, url, cache_hit, status_code, content_hash, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (source, url, 1 if cache_hit else 0, status_code, content_hash, int(time.time())),
            )


# ---------------------------------------------------------------------------
# Digest HTML
# ---------------------------------------------------------------------------

def write_digest_html(run_date: str, html: str, teaser: str, now: int) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO digest_html (run_date, html, teaser, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (run_date) DO UPDATE SET
                    html       = EXCLUDED.html,
                    teaser     = EXCLUDED.teaser,
                    updated_at = EXCLUDED.updated_at
                """,
                (run_date, html, teaser, now, now),
            )


def read_digest_html(run_date: str) -> str | None:
    """Return the HTML for a specific digest date, or None."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT html FROM digest_html WHERE run_date = %s", (run_date,)
            )
            row = cur.fetchone()
    return row[0] if row else None


def read_latest_digest_html() -> tuple[str, str] | None:
    """Return (run_date, html) for the most recent digest, or None."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_date, html FROM digest_html ORDER BY run_date DESC LIMIT 1"
            )
            row = cur.fetchone()
    return (row[0], row[1]) if row else None


def list_digest_dates() -> list[tuple[str, str]]:
    """Return [(run_date, teaser), ...] in reverse chronological order."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_date, teaser FROM digest_html ORDER BY run_date DESC"
            )
            return cur.fetchall()
