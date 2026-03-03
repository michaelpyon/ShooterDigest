"""
Auto-discovery module for ShooterDigest.
Queries SteamSpy for shooter-adjacent games in the emerging player count range.
Surfaces candidates for the Emerging Titles watchlist.
"""

import time
import logging

import requests

logger = logging.getLogger(__name__)

STEAMSPY_TAG_URL = "https://steamspy.com/api.php?request=tag&tag={tag}"

# Tags to query (one request each, with sleep between)
SHOOTER_TAGS = [
    "Extraction Shooter",
    "Tactical",
    "Battle Royale",
    "Hero Shooter",
]

# Rate limit between SteamSpy tag requests
TAG_REQUEST_SLEEP = 2  # seconds


def _fetch_tag(tag: str) -> dict:
    """Fetch SteamSpy data for a single tag. Returns empty dict on failure."""
    url = STEAMSPY_TAG_URL.format(tag=tag.replace(" ", "+"))
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "ShooterDigest/1.0"})
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        logger.warning("SteamSpy tag request failed for '%s': %s", tag, e)
        return {}


def discover_breakout_titles(
    known_app_ids: "set[int]",
    max_results: int = 6,
) -> "list[dict]":
    """Surface shooter-adjacent games showing growth signals, excluding known tracked titles.

    Args:
        known_app_ids: Set of app_ids already tracked (GAMES + EMERGING_GAMES).
        max_results: Maximum number of candidates to return.

    Returns:
        List of dicts with signal metadata, sorted by recency_ratio descending.
    """
    # --- Step 1: Query SteamSpy tag API ---
    merged: dict[int, dict] = {}

    for tag in SHOOTER_TAGS:
        logger.info("Querying SteamSpy for tag: %s", tag)
        tag_data = _fetch_tag(tag)
        for appid_str, game_data in tag_data.items():
            try:
                appid = int(appid_str)
            except (ValueError, TypeError):
                continue
            if appid not in merged:
                merged[appid] = dict(game_data)
                merged[appid]["_app_id"] = appid
        time.sleep(TAG_REQUEST_SLEEP)

    logger.info("Merged %d unique games from SteamSpy tags", len(merged))

    # --- Step 2: Filter to emerging range ---
    candidates = []
    for appid, gd in merged.items():
        # Skip already-tracked titles
        if appid in known_app_ids:
            continue

        # Parse fields (SteamSpy returns strings or ints)
        try:
            ccu = int(gd.get("ccu") or 0)
        except (ValueError, TypeError):
            ccu = 0

        try:
            avg_forever = float(gd.get("average_forever") or 0)
        except (ValueError, TypeError):
            avg_forever = 0.0

        try:
            avg_2weeks = float(gd.get("average_2weeks") or 0)
        except (ValueError, TypeError):
            avg_2weeks = 0.0

        try:
            positive = int(gd.get("positive") or 0)
        except (ValueError, TypeError):
            positive = 0

        try:
            negative = int(gd.get("negative") or 0)
        except (ValueError, TypeError):
            negative = 0

        total_reviews = positive + negative

        # Apply filters
        if not (150 <= ccu <= 12000):
            continue
        if avg_forever <= 0:
            continue
        if total_reviews < 100:
            continue

        # --- Step 3: Score for "trending up" signal ---
        recency_ratio = avg_2weeks / avg_forever if avg_forever > 0 else 0.0

        if recency_ratio >= 1.2:
            signal = "Strong"
        elif recency_ratio >= 0.8:
            signal = "Moderate"
        else:
            signal = "Watch"

        candidates.append({
            "app_id": appid,
            "name": str(gd.get("name") or "Unknown"),
            "developer": str(gd.get("developer") or ""),
            "ccu": ccu,
            "average_2weeks": avg_2weeks,
            "average_forever": avg_forever,
            "recency_ratio": recency_ratio,
            "positive": positive,
            "negative": negative,
            "signal": signal,
            "tags": {},  # SteamSpy tag API doesn't return per-game tags in this call
        })

    # --- Step 4: Sort by recency_ratio descending, return top N ---
    candidates.sort(key=lambda x: x["recency_ratio"], reverse=True)

    logger.info(
        "Discovery: %d candidates after filtering, returning top %d",
        len(candidates), max_results
    )

    return candidates[:max_results]
