"""Persistent HTTP snapshot cache for source-friendly scraping.

Backed by Postgres via db.py. Replaces the previous SQLite implementation.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time

import requests

import db

_LOCK = threading.Lock()

SOURCE_TTLS = {
    "steamcharts": 60 * 60 * 6,
    "steam_api": 60 * 15,
    "steam_news": 60 * 60,
    "reddit": 60 * 30,
    "google_news": 60 * 60,
    "default": 60 * 15,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cached_get(
    url: str,
    *,
    source: str,
    fetcher,
) -> requests.Response:
    """Return a cached response when fresh, otherwise fetch and persist it."""
    ttl = SOURCE_TTLS.get(source, SOURCE_TTLS["default"])
    cache_key = _cache_key(source, url)
    now = int(time.time())

    with _LOCK:
        row = db.read_http_cache(cache_key)

        if row and (now - row[4]) < ttl:
            db.record_fetch_run(source, url, True, row[0], row[3])
            return _build_response(url, row[0], row[1], row[2])

    # Cache miss — fetch from source (outside the lock)
    try:
        response = fetcher()
    except requests.RequestException as exc:
        status_code = 0
        if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
            status_code = exc.response.status_code
        db.record_fetch_run(source, url, False, status_code, None)
        raise
    body = response.text
    headers_json = json.dumps(dict(response.headers))
    content_hash = _content_hash(body)

    with _LOCK:
        db.write_http_cache(
            cache_key=cache_key,
            source=source,
            url=url,
            status_code=response.status_code,
            headers_json=headers_json,
            body=body,
            content_hash=content_hash,
            fetched_at=now,
        )

    db.record_fetch_run(source, url, False, response.status_code, content_hash)
    return response
