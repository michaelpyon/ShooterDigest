"""Persistent storage for ingest-once / render-many digest snapshots.

Backed by Postgres via db.py. Replaces the previous SQLite implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime

import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_payload(snapshot: dict) -> str:
    return json.dumps(snapshot, sort_keys=True)


def _content_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _extract_teaser(html: str) -> str:
    """Pull the first <li> text from digest HTML as a one-line teaser."""
    match = re.search(r"<li>(.*?)</li>", html, re.DOTALL)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        return (text[:100] + "\u2026") if len(text) > 100 else text
    return "Steam concurrents, Reddit sentiment, press coverage."


# ---------------------------------------------------------------------------
# Snapshot CRUD
# ---------------------------------------------------------------------------

def save_snapshot(
    snapshot: dict,
    *,
    pipeline: str = "weekly-digest",
    overwrite: bool = True,
) -> str:
    """Save a pipeline snapshot to Postgres. Returns the run_key."""
    run_date = snapshot.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    run_key = f"{pipeline}:{run_date}"
    payload_json = _serialize_payload(snapshot)
    content_hash = _content_hash(payload_json)
    now = int(time.time())

    db.upsert_pipeline_run(
        run_key=run_key,
        pipeline=pipeline,
        run_date=run_date,
        payload_json=payload_json,
        content_hash=content_hash,
        now=now,
        overwrite=overwrite,
    )
    return run_key


def load_snapshot(
    *,
    pipeline: str = "weekly-digest",
    run_date: str | None = None,
    run_key: str | None = None,
) -> dict | None:
    """Load a pipeline snapshot by run_key or by pipeline+date."""
    payload_json = db.load_pipeline_run(
        run_key=run_key,
        pipeline=pipeline,
        run_date=run_date,
    )
    if payload_json is None:
        return None
    return json.loads(payload_json)


def load_latest_snapshot(*, pipeline: str = "weekly-digest") -> dict | None:
    """Load the most recent snapshot for a pipeline."""
    payload_json = db.load_latest_pipeline_run(pipeline=pipeline)
    if payload_json is None:
        return None
    return json.loads(payload_json)


# ---------------------------------------------------------------------------
# Digest HTML storage (replaces filesystem export)
# ---------------------------------------------------------------------------

def store_digest_html(run_date: str, html: str) -> None:
    """Store rendered digest HTML in Postgres."""
    teaser = _extract_teaser(html)
    now = int(time.time())
    db.write_digest_html(run_date, html, teaser, now)


# ---------------------------------------------------------------------------
# Backward compatibility shims
# ---------------------------------------------------------------------------
# These functions previously wrote/read JSON to the filesystem.
# They now redirect to Postgres. Code that called export_snapshot()
# or load_exported_snapshot() keeps working without changes.

def export_snapshot(snapshot: dict, *, out_dir: str | None = None) -> str:
    """Store snapshot in Postgres. Returns a virtual path for logging."""
    run_date = snapshot.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    save_snapshot(snapshot, pipeline="weekly-digest", overwrite=True)
    return f"pg://pipeline_runs/weekly-digest:{run_date}"


def load_exported_snapshot(run_date: str, *, out_dir: str | None = None) -> dict | None:
    return load_snapshot(pipeline="weekly-digest", run_date=run_date)


def load_latest_exported_snapshot(*, out_dir: str | None = None) -> dict | None:
    return load_latest_snapshot(pipeline="weekly-digest")
