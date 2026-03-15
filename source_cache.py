"""Persistent HTTP snapshot cache for source-friendly scraping."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "data")
CACHE_DB = os.environ.get(
    "SHOOTERDIGEST_CACHE_DB",
    os.path.join(CACHE_DIR, "source_cache.sqlite3"),
)

_LOCK = threading.Lock()

SOURCE_TTLS = {
    "steamcharts": 60 * 60 * 6,
    "steam_api": 60 * 15,
    "steam_news": 60 * 60,
    "reddit": 60 * 30,
    "google_news": 60 * 60,
    "default": 60 * 15,
}


def _ensure_schema() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with sqlite3.connect(CACHE_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS http_cache (
                cache_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                headers_json TEXT NOT NULL,
                body TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                fetched_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fetch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                cache_hit INTEGER NOT NULL,
                status_code INTEGER NOT NULL,
                content_hash TEXT,
                fetched_at INTEGER NOT NULL
            )
            """
        )


def _cache_key(source: str, url: str) -> str:
    return hashlib.sha256(f"{source}:{url}".encode("utf-8")).hexdigest()


def _content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _build_response(url: str, status_code: int, headers_json: str, body: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response.headers = requests.structures.CaseInsensitiveDict(json.loads(headers_json))
    response._content = body.encode("utf-8")
    response.encoding = response.apparent_encoding or "utf-8"
    return response


def _record_fetch_run(source: str, url: str, cache_hit: bool, status_code: int, content_hash: str | None) -> None:
    with sqlite3.connect(CACHE_DB) as conn:
        conn.execute(
            """
            INSERT INTO fetch_runs (source, url, cache_hit, status_code, content_hash, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, url, 1 if cache_hit else 0, status_code, content_hash, int(time.time())),
        )


def cached_get(
    url: str,
    *,
    source: str,
    fetcher,
) -> requests.Response:
    """Return a cached response when fresh, otherwise fetch and persist it."""
    _ensure_schema()
    ttl = SOURCE_TTLS.get(source, SOURCE_TTLS["default"])
    cache_key = _cache_key(source, url)
    now = int(time.time())

    with _LOCK:
        with sqlite3.connect(CACHE_DB) as conn:
            row = conn.execute(
                """
                SELECT status_code, headers_json, body, content_hash, fetched_at
                FROM http_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if row and (now - row[4]) < ttl:
            _record_fetch_run(source, url, True, row[0], row[3])
            return _build_response(url, row[0], row[1], row[2])

    response = fetcher()
    body = response.text
    headers_json = json.dumps(dict(response.headers))
    content_hash = _content_hash(body)

    with _LOCK:
        with sqlite3.connect(CACHE_DB) as conn:
            conn.execute(
                """
                INSERT INTO http_cache (
                    cache_key, source, url, status_code, headers_json, body, content_hash, fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    status_code = excluded.status_code,
                    headers_json = excluded.headers_json,
                    body = excluded.body,
                    content_hash = excluded.content_hash,
                    fetched_at = excluded.fetched_at
                """,
                (
                    cache_key,
                    source,
                    url,
                    response.status_code,
                    headers_json,
                    body,
                    content_hash,
                    now,
                ),
            )

    _record_fetch_run(source, url, False, response.status_code, content_hash)
    return response

