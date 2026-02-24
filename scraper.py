"""Scraping and API functions for Shooter Digest."""

import re
import html as html_module
import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _http_get(url: str, headers: dict, timeout: int = 10) -> requests.Response:
    """HTTP GET with automatic retry on transient failures."""
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ShooterDigest/1.0)",
}

# Each game: name, Steam app ID, subreddit, steam_share
# steam_share: fraction of total players represented by Steam data (0.0-1.0).
# Used to extrapolate estimated total players across all platforms.
# Sources: EA/Krafton/NetEase earnings, Alinea Analytics, community trackers,
#          press releases (Tom's Hardware, PC Gamer, Dexerto, etc.)
GAMES = [
    {"name": "Counter-Strike 2", "app_id": 730, "subreddit": "cs2",
     "steam_share": 1.0, "genre": "Tactical"},
    {"name": "Apex Legends", "app_id": 1172470, "subreddit": "apexlegends",
     "steam_share": 0.25, "genre": "Battle Royale"},
    {"name": "Marvel Rivals", "app_id": 2767030, "subreddit": "marvelrivals",
     "steam_share": 0.35, "genre": "Hero Shooter"},
    {"name": "Delta Force", "app_id": 2507950, "subreddit": "DeltaForce",
     "steam_share": 0.70, "genre": "Extraction"},
    {"name": "Arc Raiders", "app_id": 1808500, "subreddit": "ArcRaiders",
     "steam_share": 0.50, "genre": "Extraction"},
    {"name": "Battlefield 6", "app_id": 2807960, "subreddit": "battlefield",
     "steam_share": 0.55, "genre": "Large-Scale"},
    {"name": "Call of Duty", "app_id": 1938090, "subreddit": "CallOfDuty",
     "steam_share": 0.15, "genre": "Large-Scale"},
    {"name": "Halo Infinite", "app_id": 1240440, "subreddit": "halo",
     "steam_share": 0.12, "genre": "Arena"},
    {"name": "Overwatch", "app_id": 2357570, "subreddit": "Overwatch",
     "steam_share": 0.20, "genre": "Hero Shooter"},
    {"name": "Rainbow Six Siege", "app_id": 359550, "subreddit": "Rainbow6",
     "steam_share": 0.35, "genre": "Tactical"},
    {"name": "PUBG: BATTLEGROUNDS", "app_id": 578080, "subreddit": "PUBATTLEGROUNDS",
     "steam_share": 0.80, "genre": "Battle Royale"},
    {"name": "The Finals", "app_id": 2073850, "subreddit": "thefinals",
     "steam_share": 0.50, "genre": "Arena"},
    {"name": "Destiny 2", "app_id": 1085660, "subreddit": "DestinyTheGame",
     "steam_share": 0.35, "genre": "Looter Shooter"},
    {"name": "Team Fortress 2", "app_id": 440, "subreddit": "tf2",
     "steam_share": 1.0, "genre": "Hero Shooter"},
    {"name": "Halo: MCC", "app_id": 976730, "subreddit": "halo",
     "steam_share": 0.30, "genre": "Arena"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_html_entities(text: str) -> str:
    """Decode all HTML entities (&nbsp;, &#x27;, &amp;, etc.) to plain text."""
    if not text:
        return ""
    return html_module.unescape(text)


def _parse_num(text: str) -> float | None:
    """Parse a number string, handling commas, +/-, HTML entities."""
    if not text:
        return None
    cleaned = text.strip().replace(",", "").replace("\u200b", "")
    cleaned = cleaned.replace("\u002b", "+").replace("&#43;", "+")
    cleaned = cleaned.replace("\xa0", "")
    if cleaned in ("-", ""):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clean_bbcode(text: str) -> str:
    """Strip BBCode / Steam markup tags and return plain text."""
    if not text:
        return ""
    # [url=X]text[/url] -> text
    text = re.sub(r"\[url=[^\]]*\](.*?)\[/url\]", r"\1", text, flags=re.S)
    # [img]...[/img] -> remove entirely
    text = re.sub(r"\[img\].*?\[/img\]", "", text, flags=re.S)
    # [previewyoutube=...][/previewyoutube] -> remove
    text = re.sub(r"\[previewyoutube=[^\]]*\]\[/previewyoutube\]", "", text)
    # [h1]...[/h1] etc -> keep inner text
    text = re.sub(r"\[/?(?:h[1-3]|b|i|u|strike|spoiler|noparse|code|quote)\]", "", text)
    # [list], [*], [olist], [table] etc -> remove tags
    text = re.sub(r"\[/?(?:list|olist|\*|table|tr|th|td|hr)\]", "", text)
    # Catch-all remaining [...] tags
    text = re.sub(r"\[/?[a-zA-Z][^\]]*\]", "", text)
    # CS2-style section headers: [ MISC ], [ GAMEPLAY ], [ MAPS ], [ SOUND ], etc.
    text = re.sub(r"\\\[\s*[A-Z][A-Z /]+\s*\\\]", "", text)
    text = re.sub(r"\[\s*[A-Z][A-Z /]+\s*\]", "", text)
    # Steam-specific placeholders: {STEAM_CLAN_IMAGE}, etc.
    text = re.sub(r"\{STEAM_CLAN_IMAGE\}[^\s]*", "", text)
    text = re.sub(r"\{[A-Z_]+\}", "", text)
    # Decode HTML entities
    text = _clean_html_entities(text)
    # Fix lone backslashes before text (BBCode section separator artifacts)
    text = re.sub(r"\\(?=[A-Za-z])", "\n", text)
    # Collapse excessive whitespace / blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _clean_reddit_text(text: str) -> str:
    """Clean Reddit comment/post text: strip URLs, image embeds, HTML entities."""
    if not text:
        return ""
    # Strip markdown image syntax: ![gif](url), ![img](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Strip markdown links but keep text: [text](url) -> text
    text = re.sub(r"\[([^\]]*)\]\(https?://[^)]*\)", r"\1", text)
    # Strip bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Strip Reddit-specific formatting artifacts
    text = re.sub(r"&#x200B;", "", text)  # zero-width space
    # Decode any remaining HTML entities
    text = _clean_html_entities(text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _is_english(text: str) -> bool:
    """Reject text with significant non-Latin characters (Cyrillic, CJK, etc.)."""
    if not text:
        return True
    sample = text[:500]  # check first 500 chars for speed
    non_latin = re.findall(
        r"[\u0400-\u04FF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF"
        r"\uAC00-\uD7AF\u0600-\u06FF\u0E00-\u0E7F]",
        sample,
    )
    return len(non_latin) <= len(sample) * 0.1


# ---------------------------------------------------------------------------
# SteamCharts: player counts + monthly trends
# ---------------------------------------------------------------------------

def get_steam_data(game: dict) -> dict | None:
    """Scrape player data + monthly trends from steamcharts.com."""
    app_id = game["app_id"]
    name = game["name"]
    url = f"https://steamcharts.com/app/{app_id}"

    try:
        resp = _http_get(url, headers=HEADERS, timeout=10)
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", name, e)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Header stats
    peak_24h = None
    peak_all = None
    for stat in soup.find_all("div", class_="app-stat"):
        num_span = stat.find("span", class_="num")
        if not num_span:
            continue
        text = stat.get_text()
        val = _parse_num(num_span.text)
        if val is None:
            continue
        if "24-hour peak" in text:
            peak_24h = int(val)
        elif "all-time peak" in text:
            peak_all = int(val)

    if peak_24h is None and peak_all is None:
        logger.error("No player counts found for %s", name)
        return None

    # Monthly trend table
    months = []
    table = soup.find("table", class_="common-table")
    if table and table.find("tbody"):
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            month_text = cells[0].get_text(strip=True)
            avg = _parse_num(cells[1].get_text(strip=True))
            gain = _parse_num(cells[2].get_text(strip=True))
            pct_raw = cells[3].get_text(strip=True)
            pct_match = re.search(r"[+-]?\d+\.?\d*", pct_raw)
            pct_gain = float(pct_match.group()) if pct_match else None
            peak = _parse_num(cells[4].get_text(strip=True))
            months.append({
                "month": month_text,
                "avg": avg,
                "gain": gain,
                "pct_gain": pct_gain,
                "peak": int(peak) if peak else None,
            })

    return {
        "name": name,
        "app_id": app_id,
        "peak_24h": peak_24h or 0,
        "peak_all": peak_all or 0,
        "months": months[:12],
    }


# ---------------------------------------------------------------------------
# Steam News API: full patch notes / announcements
# ---------------------------------------------------------------------------

def get_steam_news(app_id: int, count: int = 5) -> list[dict]:
    """Fetch recent news from Steam News API with full article content.

    Uses maxlength=0 for complete text and feeds=steam_community_announcements
    to filter to official posts. English-only filtering applied.
    """
    url = (
        f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
        f"?appid={app_id}&count={count}&maxlength=0"
        f"&feeds=steam_community_announcements&format=json"
    )

    try:
        resp = _http_get(url, headers=HEADERS, timeout=10)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Steam News failed for app %d: %s", app_id, e)
        return []

    items = data.get("appnews", {}).get("newsitems", [])
    results = []
    for item in items:
        title = item.get("title", "")
        raw_contents = item.get("contents", "")

        # Skip non-English items
        if not _is_english(title) or not _is_english(raw_contents[:300]):
            continue

        date = datetime.fromtimestamp(item.get("date", 0), tz=timezone.utc)
        cleaned = _clean_bbcode(raw_contents)

        results.append({
            "title": title,
            "date": date.strftime("%b %d, %Y"),
            "url": item.get("url", ""),
            "feed": item.get("feedlabel", ""),
            "is_patch": "patchnotes" in (item.get("tags") or []),
            "contents": cleaned,
        })

    return results


# ---------------------------------------------------------------------------
# Reddit: posts (weekly + monthly) and comments
# ---------------------------------------------------------------------------

def get_reddit_posts(subreddit: str, timeframe: str = "week", limit: int = 5) -> list[dict]:
    """Fetch top posts from a subreddit for a given timeframe.

    Args:
        subreddit: Subreddit name (without r/).
        timeframe: "week" or "month".
        limit: Number of posts to fetch.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={limit}"

    try:
        resp = _http_get(url, headers=HEADERS, timeout=10)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Reddit failed for r/%s (%s): %s", subreddit, timeframe, e)
        return []

    posts = data.get("data", {}).get("children", [])
    results = []
    for post in posts:
        d = post.get("data", {})
        title = _clean_reddit_text(d.get("title", "")) or d.get("title", "")
        results.append({
            "title": title,
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "flair": d.get("link_flair_text") or "",
            "permalink": d.get("permalink", ""),
        })

    return results


def get_reddit_comments(permalink: str, limit: int = 3) -> list[dict]:
    """Fetch top comments for a Reddit post.

    Args:
        permalink: Reddit post permalink path (e.g. /r/cs2/comments/abc123/...).
        limit: Number of top comments to fetch.
    """
    if not permalink:
        return []

    url = f"https://www.reddit.com{permalink}.json?sort=top&limit={limit}&depth=1"

    try:
        resp = _http_get(url, headers=HEADERS, timeout=10)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Reddit comments failed for %s: %s", permalink, e)
        return []

    if not isinstance(data, list) or len(data) < 2:
        return []

    children = data[1].get("data", {}).get("children", [])
    results = []
    for child in children:
        if child.get("kind") != "t1":
            continue
        d = child.get("data", {})
        body = _clean_reddit_text(d.get("body", ""))
        if not body:  # skip URL-only or empty comments
            continue
        if len(body) > 200:
            body = body[:197] + "..."
        results.append({
            "body": body,
            "score": d.get("score", 0),
            "author": d.get("author", "[deleted]"),
        })

    return results[:limit]


# ---------------------------------------------------------------------------
# Google News RSS: external press coverage
# ---------------------------------------------------------------------------

_AMBIGUOUS_NAMES = {"The Finals": "The Finals Embark game"}


def get_google_news_rss(game_name: str, limit: int = 5) -> list[dict]:
    """Fetch recent news articles about a game from Google News RSS.

    Returns articles from gaming publications (IGN, PC Gamer, Kotaku, etc.).
    Free, no API key required.
    """
    # Use specialized query for ambiguous game names
    search_term = _AMBIGUOUS_NAMES.get(game_name, f"{game_name} game")
    query = urllib.parse.quote(search_term)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={query}&hl=en-US&gl=US&ceid=US:en"
    )

    try:
        resp = _http_get(url, headers=HEADERS, timeout=10)
    except requests.RequestException as e:
        logger.error("Google News RSS failed for %s: %s", game_name, e)
        return []

    try:
        soup = BeautifulSoup(resp.text, "xml")
    except Exception:
        # Fallback if lxml not installed
        soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.find_all("item")

    # Build list of name tokens for relevance filtering
    name_tokens = set(game_name.lower().split())
    # Remove generic words from matching
    name_tokens -= {"the", "of", "and", "a", "an"}
    # Strip punctuation from tokens (e.g. "pubg:" -> "pubg")
    name_tokens = {re.sub(r'[^\w]', '', t) for t in name_tokens}
    name_tokens -= {""}  # remove empty strings if any

    results = []
    for item in items[:limit * 2]:  # fetch extra in case we filter some out
        title_tag = item.find("title")
        title = _clean_html_entities(title_tag.get_text(strip=True)) if title_tag else ""

        # Skip non-English
        if not _is_english(title):
            continue

        # Relevance: at least one name token must appear in title
        title_lower = title.lower()
        if not any(tok in title_lower for tok in name_tokens):
            continue

        # Filter out non-gaming articles (sports, Olympics, etc.)
        _non_gaming_kw = re.compile(
            r'\b(?:olympic|nba|nfl|nhl|mlb|soccer|football|basketball|'
            r'tennis|swimming|skating|medal|playoff|super bowl|world cup|'
            r'championship game|semifinal|quarterfinal|cricket|rugby)\b', re.I
        )
        if _non_gaming_kw.search(title):
            continue

        # Source / publication
        source_tag = item.find("source")
        source = source_tag.get_text(strip=True) if source_tag else ""

        # Date
        pub_date_tag = item.find("pubdate")
        date_str = ""
        date_dt = None
        if pub_date_tag and pub_date_tag.get_text(strip=True):
            try:
                date_dt = parsedate_to_datetime(pub_date_tag.get_text(strip=True))
                date_str = date_dt.strftime("%b %d, %Y")
            except (ValueError, TypeError):
                date_str = ""

        # Link
        link_tag = item.find("link")
        link = ""
        if link_tag:
            link = link_tag.get_text(strip=True) or (link_tag.next_sibling or "").strip()

        # Description — strip HTML tags and decode entities
        desc_tag = item.find("description")
        desc = ""
        if desc_tag:
            raw_desc = desc_tag.get_text(strip=True)
            desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
            desc = _clean_html_entities(desc)
            if len(desc) > 200:
                desc = desc[:197] + "..."

        results.append({
            "title": title,
            "source": source,
            "date": date_str,
            "date_dt": date_dt,
            "url": link,
            "description": desc,
        })

        if len(results) >= limit:
            break

    # Sort by publication date descending (newest first), articles with no date go last
    results.sort(key=lambda x: x["date_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return results
