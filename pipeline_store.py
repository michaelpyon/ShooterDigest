"""Persistent storage for ingest-once / render-many digest snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PIPELINE_DB = os.environ.get(
    "SHOOTERDIGEST_PIPELINE_DB",
    os.path.join(DATA_DIR, "pipeline.sqlite3"),
)


def _ensure_schema() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(PIPELINE_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_key TEXT PRIMARY KEY,
                pipeline TEXT NOT NULL,
                run_date TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_date
            ON pipeline_runs(pipeline, run_date DESC)
            """
        )


def _serialize_payload(snapshot: dict) -> str:
    return json.dumps(snapshot, sort_keys=True)


def _content_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def save_snapshot(
    snapshot: dict,
    *,
    pipeline: str = "weekly-digest",
    overwrite: bool = True,
) -> str:
    _ensure_schema()
    run_date = snapshot.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    run_key = f"{pipeline}:{run_date}"
    payload_json = _serialize_payload(snapshot)
    content_hash = _content_hash(payload_json)
    now = int(time.time())

    with sqlite3.connect(PIPELINE_DB) as conn:
        if overwrite:
            conn.execute(
                """
                INSERT INTO pipeline_runs (
                    run_key, pipeline, run_date, payload_json, content_hash, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    content_hash = excluded.content_hash,
                    updated_at = excluded.updated_at
                """,
                (run_key, pipeline, run_date, payload_json, content_hash, now, now),
            )
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO pipeline_runs (
                    run_key, pipeline, run_date, payload_json, content_hash, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_key, pipeline, run_date, payload_json, content_hash, now, now),
            )

    return run_key


def load_snapshot(
    *,
    pipeline: str = "weekly-digest",
    run_date: str | None = None,
    run_key: str | None = None,
) -> dict | None:
    _ensure_schema()
    query = None
    params = None

    if run_key:
        query = "SELECT payload_json FROM pipeline_runs WHERE run_key = ?"
        params = (run_key,)
    elif run_date:
        query = """
            SELECT payload_json
            FROM pipeline_runs
            WHERE pipeline = ? AND run_date = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """
        params = (pipeline, run_date)
    else:
        return None

    with sqlite3.connect(PIPELINE_DB) as conn:
        row = conn.execute(query, params).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def load_latest_snapshot(*, pipeline: str = "weekly-digest") -> dict | None:
    _ensure_schema()
    with sqlite3.connect(PIPELINE_DB) as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM pipeline_runs
            WHERE pipeline = ?
            ORDER BY run_date DESC, updated_at DESC
            LIMIT 1
            """,
            (pipeline,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def export_snapshot(snapshot: dict, *, out_dir: str | None = None) -> str:
    run_date = snapshot.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    export_dir = os.path.join(out_dir or DEFAULT_OUTPUT_DIR, "pipeline")
    os.makedirs(export_dir, exist_ok=True)
    path = os.path.join(export_dir, f"{run_date}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return path


def load_exported_snapshot(run_date: str, *, out_dir: str | None = None) -> dict | None:
    path = os.path.join(out_dir or DEFAULT_OUTPUT_DIR, "pipeline", f"{run_date}.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_exported_snapshot(*, out_dir: str | None = None) -> dict | None:
    export_dir = os.path.join(out_dir or DEFAULT_OUTPUT_DIR, "pipeline")
    if not os.path.isdir(export_dir):
        return None

    files = sorted(
        [
            name
            for name in os.listdir(export_dir)
            if name.endswith(".json") and len(name) >= 15
        ],
        reverse=True,
    )
    for name in files:
        path = os.path.join(export_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
    return None
