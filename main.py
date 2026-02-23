"""Shooter Digest - Weekly competitive shooter player tracker."""

import os
import re
import json
import time
import html as html_mod
import logging
import calendar as cal_mod
from datetime import datetime

from scraper import (
    GAMES,
    get_steam_data,
    get_steam_news,
    get_reddit_posts,
    get_reddit_comments,
    get_google_news_rss,
)

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

DELAY_BETWEEN_REQUESTS = 2  # seconds


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(n: int | float | None) -> str:
    if n is None:
        return "-"
    if isinstance(n, float):
        return f"{int(n):,}"
    return f"{n:,}"


def _fmt_k(n: float | None) -> str:
    if n is None:
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:.0f}"


def _trend_arrow(pct: float | None) -> tuple[str, str]:
    if pct is None:
        return ("?", "neutral")
    if pct > 2:
        return ("\u25b2", "up")
    if pct < -2:
        return ("\u25bc", "down")
    return ("\u25b6", "flat")


def _esc(text: str) -> str:
    # Decode HTML entities first, then escape for HTML output
    text = html_mod.unescape(text)
    return html_mod.escape(text)


def _sanitize_text(text: str) -> str:
    """Final text sanitization: decode entities, fix formatting artifacts.

    Apply before any text is rendered to ensure readable plain English.
    """
    if not text:
        return ""
    # Decode any remaining HTML entities
    text = html_mod.unescape(text)
    # Strip leading backslashes from cleaned BBCode ("\\Fixed" -> "Fixed")
    text = re.sub(r"(?<=\s)\\+(?=[A-Za-z])", "", text)
    text = re.sub(r"^\\+(?=[A-Za-z])", "", text)
    # Fix missing spaces after punctuation ("loot!The" -> "loot! The")
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    # Remove leftover bullet characters
    text = text.replace("\u25cf", "").replace("\u2022", "")
    # Strip zero-width spaces and other invisible chars
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Sentiment analysis
# ---------------------------------------------------------------------------

_POSITIVE_KW = re.compile(
    r'\b(?:love|amazing|best|great|excited|improve|improving|growing|launch|'
    r'new season|buff|returns|celebrates|incredible|perfect|beautiful|'
    r'gorgeous|masterpiece|appreciation|underrated|fantastic|excellent|'
    r'awesome|thriving|hype|hyped|praised|popular|record|surge|surging|'
    r'win|winning|won|victory|epic|stunning|brilliant|outstanding)\b',
    re.I
)

_NEGATIVE_KW = re.compile(
    r'\b(?:broken|nerf|nerfed|dead|worst|decline|declining|bug|bugs|issue|issues|'
    r'complaint|shut down|disappointed|removes|controversy|terrible|awful|garbage|'
    r'trash|unplayable|ruined|rant|frustrat|anger|angry|outrage|boycott|'
    r'dropping|crashed|exploit|cheat|hacked|pay.to.win|p2w|scam|predatory|'
    r'toxic|ban|banned|delay|delayed|cancel|cancelled|failing|failed|worse)\b',
    re.I
)


def _analyze_sentiment(text: str) -> str:
    """Keyword-based sentiment scoring. Returns 'positive', 'negative', or 'neutral'."""
    if not text:
        return "neutral"
    pos = len(_POSITIVE_KW.findall(text))
    neg = len(_NEGATIVE_KW.findall(text))
    if pos > neg and pos > 0:
        return "positive"
    if neg > pos and neg > 0:
        return "negative"
    return "neutral"


SENTIMENT_COLORS = {
    "positive": ("#4ade80", "#1e5f2e"),   # green
    "negative": ("#f87171", "#5f1e1e"),   # red
    "neutral":  ("#94a3b8", "#2d3748"),   # gray
}


def _sentiment_css(sentiment: str) -> tuple[str, str]:
    """Return (foreground_color, background_color) for a sentiment value."""
    return SENTIMENT_COLORS.get(sentiment, SENTIMENT_COLORS["neutral"])


# Genre colors: (text_color, background_color)
GENRE_COLORS = {
    "Battle Royale":  ("#fbbf24", "#3b2f0a"),   # amber
    "Hero Shooter":   ("#c084fc", "#2e1065"),    # purple
    "Tactical":       ("#38bdf8", "#0c2d48"),    # sky blue
    "Extraction":     ("#fb923c", "#3b1f0a"),    # orange
    "Arena":          ("#34d399", "#0a3b2b"),    # emerald
    "Large-Scale":    ("#4ade80", "#0a3b1f"),    # green
    "Looter Shooter": ("#f472b6", "#3b0a2e"),    # pink
    "Other":          ("#94a3b8", "#1e293b"),    # gray
}

# Short labels for compact badges
GENRE_SHORT = {
    "Battle Royale": "BR",
    "Hero Shooter": "Hero",
    "Tactical": "Tactical",
    "Extraction": "Extract",
    "Arena": "Arena",
    "Large-Scale": "Large",
    "Looter Shooter": "Looter",
    "Other": "Other",
}


def _genre_badge_html(genre: str) -> str:
    """Return a small colored badge for a genre."""
    fg, bg = GENRE_COLORS.get(genre, GENRE_COLORS["Other"])
    short = GENRE_SHORT.get(genre, genre)
    return f'<span class="genre-badge" style="color:{fg};background:{bg}">{short}</span>'


# ---------------------------------------------------------------------------
# Game Lifecycle States (#4)
# ---------------------------------------------------------------------------

LIFECYCLE_STATES = {
    "Counter-Strike 2": "Live",
    "PUBG: BATTLEGROUNDS": "Live",
    "Arc Raiders": "Live",
    "Apex Legends": "Maintenance",
    "Delta Force": "Live",
    "Marvel Rivals": "Live",
    "Overwatch": "Live",
    "Rainbow Six Siege": "Live",
    "Battlefield 6": "Live",
    "Team Fortress 2": "Legacy",
    "Call of Duty": "Live",
    "The Finals": "Live",
    "Destiny 2": "Maintenance",
    "Halo: MCC": "Legacy",
    "Halo Infinite": "Sunset",
}

LIFECYCLE_COLORS = {
    "Live": ("#4ade80", "#1a3a2a"),      # green
    "Maintenance": ("#fbbf24", "#3a3520"),  # yellow
    "Sunset": ("#f87171", "#3a1a1a"),      # red
    "Legacy": ("#94a3b8", "#2a2e35"),      # gray
    "Pre-Launch": ("#60a5fa", "#1a2a3a"),  # blue
}

LIFECYCLE_EMOJI = {
    "Live": "\U0001f7e2",
    "Maintenance": "\U0001f7e1",
    "Sunset": "\U0001f534",
    "Legacy": "\u26aa",
    "Pre-Launch": "\U0001f535",
}


def _lifecycle_badge_html(name: str) -> str:
    state = LIFECYCLE_STATES.get(name)
    if not state:
        return ""
    fg, bg = LIFECYCLE_COLORS.get(state, ("#94a3b8", "#2a2e35"))
    return f' <span class="lifecycle-badge" style="color:{fg};background:{bg}">{state}</span>'


# ---------------------------------------------------------------------------
# Event Annotations for big movers (#8)
# ---------------------------------------------------------------------------

EVENT_ANNOTATIONS = {
    "Overwatch": "+76.4% \u2190 Loverwatch event + OWCS S2 kickoff + sub-role passives patch",
    "Arc Raiders": "-18.6% \u2190 Post-launch decay. Second Expedition season announced Mar 1.",
    "Delta Force": "+14.0% \u2190 RED DAY event + Season Morphosis live",
    "Battlefield 6": "-22.6% \u2190 Season 2 launched Feb 17 but failing to retain",
    "Halo: MCC": "-21.3% \u2190 Legacy title, Halo 2 Digsite content drop had limited impact",
    "Halo Infinite": "-9.3% \u2190 Post-final update (Nov 2025). Expected attrition curve.",
    "Destiny 2": "-23.7% \u2190 Continued structural decline pre-Marathon (Mar 5)",
}


# ---------------------------------------------------------------------------
# Platform multiplier notes (#7)
# ---------------------------------------------------------------------------

PLATFORM_NOTES = {
    "Counter-Strike 2": "Steam-only title",
    "PUBG: BATTLEGROUNDS": "Krafton earnings; mobile is separate. Console ~20% of PC.",
    "Arc Raiders": "Steam + Epic. Est. 50/50 split based on Embark data.",
    "Apex Legends": "EA earnings (Q3 2025). Console-heavy (PS/Xbox ~75%).",
    "Delta Force": "NetEase; primarily PC (Steam + launcher). ~30% non-Steam.",
    "Marvel Rivals": "NetEase; PS/Xbox ~65% based on launch week platform split.",
    "Overwatch": "Blizzard earnings. Console-dominant franchise (~80%).",
    "Rainbow Six Siege": "Ubisoft earnings. Console ~65% historically.",
    "Battlefield 6": "EA earnings. Console ~45% for BF franchise.",
    "Team Fortress 2": "Steam-only title (legacy)",
    "Call of Duty": "Activision earnings. Console-dominant franchise (~85%).",
    "The Finals": "Embark data. Steam ~50%, rest PS/Xbox.",
    "Destiny 2": "Bungie data. Console ~65% (PS dominant).",
    "Halo: MCC": "Xbox Game Studios. Steam ~30%, Xbox ~70%.",
    "Halo Infinite": "Xbox Game Studios. Steam ~12%, Xbox ~88%.",
}


# ---------------------------------------------------------------------------
# Aggregate game sentiment (#5)
# ---------------------------------------------------------------------------

def _compute_game_sentiment(r: dict) -> str:
    """Aggregate sentiment across news, press, and Reddit for a game."""
    pos = 0
    neg = 0
    for n in r.get("news", []):
        s = _analyze_sentiment(n.get("title", "") + " " + (n.get("contents", "") or "")[:200])
        if s == "positive": pos += 1
        elif s == "negative": neg += 1
    for a in r.get("external_news", []):
        s = _analyze_sentiment(a.get("title", ""))
        if s == "positive": pos += 1
        elif s == "negative": neg += 1
    for p in r.get("reddit_week", []) + r.get("reddit_month", []):
        s = _analyze_sentiment(p.get("title", ""))
        if s == "positive": pos += 1
        elif s == "negative": neg += 1
    if pos > neg and pos > 0:
        return "positive"
    if neg > pos and neg > 0:
        return "negative"
    return "mixed"


# ---------------------------------------------------------------------------
# Inline mini-sparkline for trend column (#6)
# ---------------------------------------------------------------------------

def _inline_sparkline_svg(months_data: list[dict], css_class: str = "neutral") -> str:
    """Generate a tiny inline SVG sparkline (~60x16px) from monthly avg data."""
    avgs = [m.get("avg") for m in months_data if m.get("avg") is not None]
    if len(avgs) < 2:
        return ""
    # Use last 4 data points
    avgs = avgs[:4]
    if len(avgs) < 2:
        return ""
    w, h = 48, 14
    mn, mx = min(avgs), max(avgs)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(avgs):
        x = i * w / (len(avgs) - 1)
        y = h - 1 - ((v - mn) / rng) * (h - 2)
        pts.append(f"{x:.1f},{y:.1f}")
    color = {"up": "#4ade80", "down": "#f87171", "flat": "#fbbf24"}.get(css_class, "#94a3b8")
    return (
        f'<svg class="inline-spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# News summary extraction
# ---------------------------------------------------------------------------

def _extract_news_summary(news_item: dict) -> str:
    """Extract a readable 2-3 sentence summary from a news item's contents.

    Replaces raw content[:150] truncation with proper sentence extraction.
    Skips boilerplate and returns substantive sentences.
    """
    contents = news_item.get("contents", "")
    title = news_item.get("title", "")

    if not contents:
        return ""

    # Sanitize input
    contents = _sanitize_text(contents)

    # Split into sentences (avoid splitting on version numbers like 1.2.1.0)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', contents[:2000])

    # Filter out boilerplate
    boilerplate_kw = re.compile(
        r'\b(?:click here|subscribe|follow us|join our|discord|wishlist|'
        r'add to your|steam store|coming to|available on|check out our|'
        r'stay tuned|see you|thank you for|please note|note:)\b',
        re.I
    )

    # Filter out sentences that are just the title repeated
    title_lower = title.lower().strip()

    good = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15 or len(s) > 300:
            continue
        if boilerplate_kw.search(s):
            continue
        # Skip if it's basically just the title
        if s.lower().strip().startswith(title_lower[:30]):
            continue
        good.append(s)

    # Take first 2-3 good sentences, up to ~250 chars total
    result_parts = []
    total_len = 0
    for s in good[:3]:
        if total_len + len(s) > 250 and result_parts:
            break
        result_parts.append(s)
        total_len += len(s)

    result = " ".join(result_parts)
    if len(result) > 280:
        result = result[:277] + "..."
    return result


# ---------------------------------------------------------------------------
# SVG sparkline chart
# ---------------------------------------------------------------------------

_SPARKLINE_COLORS = {
    "up": ("#4ade80", "rgba(74,222,128,0.12)"),
    "down": ("#f87171", "rgba(248,113,113,0.12)"),
    "flat": ("#fbbf24", "rgba(251,191,36,0.12)"),
    "neutral": ("#8f98a0", "rgba(143,152,160,0.12)"),
}


def _generate_sparkline_svg(avg_trend: list[dict], trend_css: str) -> str:
    """Generate an inline SVG sparkline chart for monthly player trends.

    Args:
        avg_trend: List of month dicts (oldest first) with 'avg' and 'month' keys.
        trend_css: One of "up", "down", "flat", "neutral" for coloring.

    Returns:
        HTML string with <svg> element, or empty string if insufficient data.
    """
    # Filter to entries with valid avg values
    points = [(m.get("month", ""), m.get("avg")) for m in avg_trend if m.get("avg") is not None]
    if len(points) < 2:
        return ""

    stroke, fill = _SPARKLINE_COLORS.get(trend_css, _SPARKLINE_COLORS["neutral"])

    # Chart dimensions
    w, h = 240, 55
    pad_x, pad_top, pad_bot = 12, 10, 18  # bottom padding for labels

    # Extract values and compute scale
    values = [p[1] for p in points]
    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min if v_max != v_min else 1  # avoid div by zero

    # Map data points to pixel coordinates
    chart_h = h - pad_top - pad_bot
    chart_w = w - pad_x * 2
    n = len(points)
    coords = []
    for i, (_, v) in enumerate(points):
        x = pad_x + (i / (n - 1)) * chart_w if n > 1 else pad_x + chart_w / 2
        y = pad_top + chart_h - ((v - v_min) / v_range) * chart_h
        coords.append((round(x, 1), round(y, 1)))

    # Build polyline points string
    polyline_pts = " ".join(f"{x},{y}" for x, y in coords)

    # Build filled polygon (area under the curve)
    bottom_y = pad_top + chart_h
    polygon_pts = polyline_pts + f" {coords[-1][0]},{bottom_y} {coords[0][0]},{bottom_y}"

    # Month labels
    labels_svg = ""
    for i, (month_text, _) in enumerate(points):
        x = coords[i][0]
        # Shorten month label
        if month_text == "Last 30 Days":
            label = datetime.now().strftime("%b")
        else:
            try:
                dt = datetime.strptime(month_text, "%B %Y")
                label = dt.strftime("%b")
            except ValueError:
                label = month_text[:3]
        labels_svg += (
            f'<text x="{x}" y="{h - 2}" text-anchor="middle" '
            f'fill="#8f98a0" font-size="8" font-family="sans-serif">{label}</text>\n'
        )

    # Data point dots
    dots_svg = ""
    for x, y in coords:
        dots_svg += f'<circle cx="{x}" cy="{y}" r="3" fill="{stroke}" />\n'

    # Value label at last point
    last_x, last_y = coords[-1]
    last_val = _fmt_k(values[-1])
    label_y = max(last_y - 6, 8)  # ensure label stays in view
    value_label = (
        f'<text x="{last_x}" y="{label_y}" text-anchor="middle" '
        f'fill="{stroke}" font-size="9" font-weight="bold" font-family="sans-serif">'
        f'{last_val}</text>\n'
    )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">
  <polygon points="{polygon_pts}" fill="{fill}" />
  <polyline points="{polyline_pts}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
  {dots_svg}
  {labels_svg}
  {value_label}
</svg>'''


# ---------------------------------------------------------------------------
# Reddit post categorization
# ---------------------------------------------------------------------------

def _categorize_post(title: str, flair: str, score: int = 0) -> str:
    """Categorize a Reddit post based on title and flair keywords.

    Returns one of: NEWS, CRITICISM, PRAISE, CLIP, CREATIVE, HUMOR, DISCUSSION, OTHER.
    Priority: NEWS > CRITICISM > PRAISE > CLIP > CREATIVE > HUMOR > DISCUSSION > OTHER
    """
    t = title.lower()
    f = flair.lower()

    # NEWS
    if any(kw in f for kw in ("news", "announcement", "update", "patch", "dev", "official")):
        return "NEWS"
    if any(kw in t for kw in ("patch notes", "dev update", "season ", "announced",
                              "new season", "maintenance", "hotfix", "server",
                              "official", "update ", "release date", "roadmap")):
        return "NEWS"

    # CRITICISM
    if any(kw in t for kw in ("fix ", "broken", "worst", "rant", "complaint", "nerf ",
                              "nerfed", "issue", "disappointed", "unplayable", "reminder:",
                              "why can't", "why won't", "please fix", "stop ", "ruined",
                              "terrible", "awful", "garbage", "trash ", "dead game")):
        return "CRITICISM"

    # PRAISE
    if any(kw in t for kw in ("love ", "amazing", "best ", "incredible", "perfect",
                              "thank", "appreciation", "shoutout", "underrated",
                              "beautiful", "gorgeous", "masterpiece")):
        return "PRAISE"

    # CLIP
    if any(kw in f for kw in ("clip", "highlight", "gameplay", "play of the game")):
        return "CLIP"
    if any(kw in t for kw in ("ace", "clutch", "insane clip", "hip fire", "headshot",
                              "1v5", "1v4", "1v3", "my best", "watch this",
                              "check this", "no scope", "collateral")):
        return "CLIP"

    # CREATIVE
    if any(kw in f for kw in ("art", "creative", "cosplay", "fan")):
        return "CREATIVE"
    if any(kw in t for kw in ("cosplay", "fan art", "fanart", "animation",
                              "3d print", "drawing", "painted", "i made",
                              "sculpture", "tattoo")):
        return "CREATIVE"

    # HUMOR
    if any(kw in f for kw in ("meme", "humor", "funny", "fluff", "satire")):
        return "HUMOR"
    if any(kw in t for kw in ("lmao", "lol ", "bruh", "meme", "shitpost",
                              "did a 14", "literally ", "bro ")):
        return "HUMOR"

    # DISCUSSION
    if any(kw in f for kw in ("discussion", "question", "help", "advice", "guide")):
        return "DISCUSSION"
    if t.rstrip().endswith("?") or t.startswith("what ") or t.startswith("how "):
        return "DISCUSSION"

    return "OTHER"


def _generate_aggregate_sparkline(results: list[dict]) -> str:
    """Generate a larger SVG sparkline showing total market trend.

    Sums average player counts across all games for each month in the overlapping range.
    Returns an HTML string with <svg> element, or empty string if insufficient data.
    """
    if not results:
        return ""

    # Find the common month range across all games (use the minimum available months)
    max_months = 12
    all_month_data = []
    for r in results:
        months = r.get("months", [])
        valid = [(i, m) for i, m in enumerate(months[:max_months]) if m.get("avg") is not None]
        all_month_data.append(valid)

    if not all_month_data:
        return ""

    # Find common range length
    min_len = min(len(md) for md in all_month_data) if all_month_data else 0
    if min_len < 2:
        return ""

    # Sum averages for each month position
    month_sums = []
    for i in range(min_len):
        total = 0
        month_label = ""
        for game_months in all_month_data:
            _, m = game_months[i]
            total += m.get("avg", 0)
            if not month_label:
                month_label = m.get("month", "")
        month_sums.append({"month": month_label, "avg": total})

    # Reverse so oldest is first (for left-to-right chronological display)
    month_sums.reverse()

    # Chart dimensions (larger than per-game sparklines)
    w, h = 350, 70
    pad_x, pad_top, pad_bot = 16, 12, 20
    stroke = "#60a5fa"  # blue
    fill_color = "rgba(96,165,250,0.12)"

    values = [p["avg"] for p in month_sums]
    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min if v_max != v_min else 1

    chart_h = h - pad_top - pad_bot
    chart_w = w - pad_x * 2
    n = len(month_sums)
    coords = []
    for i, v in enumerate(values):
        x = pad_x + (i / (n - 1)) * chart_w if n > 1 else pad_x + chart_w / 2
        y = pad_top + chart_h - ((v - v_min) / v_range) * chart_h
        coords.append((round(x, 1), round(y, 1)))

    polyline_pts = " ".join(f"{x},{y}" for x, y in coords)
    bottom_y = pad_top + chart_h
    polygon_pts = polyline_pts + f" {coords[-1][0]},{bottom_y} {coords[0][0]},{bottom_y}"

    # Month labels (show every other to avoid crowding)
    labels_svg = ""
    step = max(1, n // 6)  # show ~6 labels max
    for i, m in enumerate(month_sums):
        if i % step != 0 and i != n - 1:
            continue
        x = coords[i][0]
        month_text = m["month"]
        if month_text == "Last 30 Days":
            label = datetime.now().strftime("%b")
        else:
            try:
                dt = datetime.strptime(month_text, "%B %Y")
                label = dt.strftime("%b")
            except ValueError:
                label = month_text[:3]
        labels_svg += (
            f'<text x="{x}" y="{h - 2}" text-anchor="middle" '
            f'fill="#8f98a0" font-size="8" font-family="sans-serif">{label}</text>\n'
        )

    # Dots
    dots_svg = ""
    for i, (x, y) in enumerate(coords):
        if i % step == 0 or i == n - 1:
            dots_svg += f'<circle cx="{x}" cy="{y}" r="3" fill="{stroke}" />\n'

    # Value labels at start and end
    first_val = _fmt_k(values[0])
    last_val = _fmt_k(values[-1])
    first_y = max(coords[0][1] - 6, 8)
    last_y = max(coords[-1][1] - 6, 8)
    value_labels = (
        f'<text x="{coords[0][0]}" y="{first_y}" text-anchor="start" '
        f'fill="#8f98a0" font-size="8" font-family="sans-serif">{first_val}</text>\n'
        f'<text x="{coords[-1][0]}" y="{last_y}" text-anchor="end" '
        f'fill="{stroke}" font-size="9" font-weight="bold" font-family="sans-serif">{last_val}</text>\n'
    )

    return f'''<div class="aggregate-chart">
  <div class="aggregate-label">Total Market — Avg Concurrent Players on Steam (All Tracked Titles)<br><span style="font-size:0.6rem;font-weight:400;color:#556b7d">Steam Concurrent Players (Source: SteamDB)</span></div>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
    <polygon points="{polygon_pts}" fill="{fill_color}" />
    <polyline points="{polyline_pts}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
    {dots_svg}
    {labels_svg}
    {value_labels}
  </svg>
</div>'''


# Category display colors (for HTML rendering)
CATEGORY_COLORS = {
    "NEWS": ("#3b82f6", "#1e3a5f"),         # blue
    "CRITICISM": ("#f87171", "#5f1e1e"),     # red
    "PRAISE": ("#4ade80", "#1e5f2e"),        # green
    "HUMOR": ("#fbbf24", "#5f4b00"),         # yellow
    "CLIP": ("#a78bfa", "#3b1e5f"),          # purple
    "CREATIVE": ("#f472b6", "#5f1e4a"),      # pink
    "DISCUSSION": ("#94a3b8", "#2d3748"),    # gray
    "OTHER": ("#64748b", "#1e293b"),         # dim gray
}


# ---------------------------------------------------------------------------
# Trend hypothesis engine
# ---------------------------------------------------------------------------

def _generate_trend_hypothesis(r: dict) -> str:
    """Generate a hypothesis explaining WHY player counts are moving.

    Connects player data trends to developer activity timeline.
    """
    dev = r.get("dev_comms", {})
    trend_pct = r.get("trend_pct")
    pct_all = r.get("pct_all", 0)
    news = r.get("news", [])

    if trend_pct is None:
        return "Insufficient data to determine trend drivers."

    growing = trend_pct > 2
    declining = trend_pct < -2
    sharply_declining = trend_pct < -10
    surging = trend_pct > 10
    stable = not growing and not declining

    has_season = dev.get("has_new_season", False)
    has_content = dev.get("has_new_content", False)
    has_balance = dev.get("has_balance_changes", False)
    has_bugs = dev.get("has_bug_fixes", False)
    has_news = bool(news)
    season_name = dev.get("season_name", "")
    content_details = dev.get("new_content_details", "")

    # Compute days since latest news
    latest_date = ""
    if news:
        latest_date = news[0].get("date", "")

    if surging and has_season:
        detail = f" ({season_name})" if season_name else ""
        return f"Surge likely driven by new season launch{detail}. Fresh content typically triggers a player spike in the first 2-4 weeks."

    if growing and has_season:
        detail = f" ({season_name})" if season_name else ""
        return f"Growth likely driven by{detail} season launch bringing returning and new players."

    if growing and has_content:
        detail = f" ({content_details})" if content_details else ""
        return f"New content{detail} appears to be driving engagement. Player interest tends to spike around major content drops."

    if growing and has_balance:
        return "Growth coincides with recent balance changes — meta shifts often re-engage lapsed players curious about the new state of play."

    if growing and has_bugs and not has_content and not has_season:
        return "Growth despite no major content — bug fixes and quality-of-life patches may be improving player retention."

    if growing and not has_news:
        return "Organic growth with no recent content updates — may indicate external factors such as streamer coverage, a sale, or issues with competing titles."

    if growing:
        return "Growth aligns with recent developer activity. Sustained engagement will depend on content cadence."

    if sharply_declining and pct_all > 40:
        return "Sharp decline from elevated levels — likely post-launch or post-season normalization as initial hype fades. This is a typical pattern."

    if sharply_declining and has_season:
        return "Declining sharply despite new season content — may indicate content quality concerns or post-launch player churn exceeding new player acquisition."

    if declining and not has_news:
        date_str = f" since {latest_date}" if latest_date else ""
        return f"Decline coincides with no developer updates{date_str} — possible content drought. Players may be migrating to competing titles with fresher content."

    if declining and has_season:
        return "Declining despite active season — may signal that the current content cycle is not resonating with the player base, or competition is pulling players away."

    if declining and has_content:
        return "Declining despite new content additions — the updates may not be addressing core player concerns, or the player base is in a natural contraction cycle."

    if declining:
        return "Decline aligns with typical end-of-content-cycle patterns. Watch for upcoming announcements that could reverse the trend."

    if stable and has_season:
        return "Stable player base despite new season — suggests the game has found its core audience. Season content is maintaining but not expanding the player pool."

    if stable and not has_news:
        return "Stable without recent updates — indicates a loyal core player base. Growth will likely require fresh content or events."

    if stable:
        return "Stable player base suggests healthy retention with existing content. The game is maintaining its audience effectively."

    return "Mixed signals — insufficient data to determine a clear trend driver."


# ---------------------------------------------------------------------------
# Developer comms analysis
# ---------------------------------------------------------------------------

def _extract_upcoming_detail(item: dict) -> str:
    """Extract a substantive summary sentence from a news item's contents.

    Instead of just returning the article title, finds 1-2 sentences that
    describe what is actually coming/launching.
    """
    title = item.get("title", "")
    contents = item.get("contents", "")
    date = item.get("date", "")

    if not contents:
        return f"{title} ({date})" if date else title

    # Split into sentences carefully (avoid splitting on version numbers like 1.2.1.0)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', contents[:1500])

    # Look for sentences with forward-looking content
    future_kw = r'\b(?:will|introduces?|begins?|arriving|coming|launches?|featuring|includes?|brings?|adds?|starting|now live|now available)\b'
    future_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20 or len(s) > 300:
            continue
        if re.search(future_kw, s, re.I):
            # Skip overly generic sentences
            if not re.search(r'click|subscribe|follow us|join|discord', s, re.I):
                future_sentences.append(s)

    if future_sentences:
        detail = future_sentences[0]
        if len(detail) > 180:
            detail = detail[:177] + "..."
        return detail

    # Fallback: first substantial sentence from contents
    for s in sentences:
        s = s.strip()
        if 20 < len(s) < 250:
            if not re.search(r'click|subscribe|follow us|join|discord|welcome to', s, re.I):
                if len(s) > 180:
                    s = s[:177] + "..."
                return s

    # Last resort: title + date
    return f"{title} ({date})" if date else title


def _analyze_dev_comms(news: list[dict]) -> dict:
    """Scan news items for developer communication signals.

    Returns structured summary with specific extracted details, not just flags.
    """
    result = {
        "has_new_season": False,
        "has_new_map": False,
        "has_balance_changes": False,
        "has_new_content": False,
        "has_bug_fixes": False,
        "has_upcoming_event": False,
        "season_name": "",
        "new_content_details": "",
        "balance_details": "",
        "upcoming_details": "",
        "upcoming_summary": "",  # kept for backward compat
        "content_summary": "",
        "bug_fix_count": 0,
    }

    if not news:
        return result

    content_parts = []
    upcoming_items = []

    for item in news:
        title_orig = item.get("title", "")
        title = title_orig.lower()
        contents_orig = item.get("contents", "")
        contents = contents_orig.lower()
        combined = title + " " + contents[:2000]

        # Season detection — extract season name
        if re.search(r"\bseason\s*[\d.]+|new season|season \w+ begins|season launch", combined):
            result["has_new_season"] = True
            season_match = re.search(
                r'[Ss]eason\s*[\d.]+(?:\s*[:\-–]\s*([A-Z][A-Za-z\s&]+))?',
                title_orig
            )
            if season_match:
                result["season_name"] = season_match.group().strip()

        # New map — extract map name if possible
        if re.search(r"\bnew map|introducing.*map|map rework|new arena", combined):
            result["has_new_map"] = True
            map_match = re.search(r'(?:new map|map)\s*[:\-–]?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})', contents_orig[:500])
            if map_match:
                content_parts.append(f"new map {map_match.group(1).strip()}")
            else:
                content_parts.append("new map")

        # Balance changes — extract specific items
        if re.search(r"\bbalance|nerf|buff|tuning|adjusted|designer.?s?\s*notes", combined):
            result["has_balance_changes"] = True
            # Try to extract specific balance targets
            balance_items = re.findall(
                r'(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:has been|was|is)\s+'
                r'(?:buff|nerf|adjust|tuned|changed)',
                contents_orig[:1500]
            )
            if balance_items:
                result["balance_details"] = ", ".join(balance_items[:3])

        # New content — extract specific names
        content_match = re.search(
            r'\bnew (?:weapon|hero|operator|character|agent|legend|mode|gadget|vehicle|'
            r'specialist|ability|item)\b',
            combined
        )
        if content_match or re.search(r'\bintroducing\b', combined):
            result["has_new_content"] = True
            # Extract what was introduced — capture proper-noun-style names only
            # (up to 4 capitalized words), not full sentences
            new_items = re.findall(
                r'(?:introducing|new (?:hero|operator|weapon|map|mode|character|legend|agent))'
                r'\s*[:\-–]?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})',
                contents_orig[:1500]
            )
            if new_items:
                result["new_content_details"] = ", ".join(
                    item.strip() for item in new_items[:3]
                )

        # Bug fixes — count for scope
        if re.search(r'\b(?:bug\s*)?fix|hotfix|resolved|addressed|patched|stability', combined):
            result["has_bug_fixes"] = True
            fix_count = len(re.findall(r'\bfix(?:ed|es)?\b', contents))
            result["bug_fix_count"] = max(result["bug_fix_count"], fix_count)

        # Upcoming/forward-looking events
        upcoming_match = re.search(
            r"(?:begins?|starts?|launches?|arriving|coming)\s+"
            r"(?:on\s+)?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}|\d{1,2}/\d{1,2})",
            combined
        )
        if upcoming_match:
            result["has_upcoming_event"] = True
            upcoming_items.append(item)

        # Also catch "coming soon", "next week", "now live" etc.
        if re.search(r"\bcoming soon|next (?:week|month|update)|early access|beta|preview|now live|now available", combined):
            if not upcoming_items or upcoming_items[-1] is not item:
                result["has_upcoming_event"] = True
                upcoming_items.append(item)

    # Build upcoming details with substance
    if upcoming_items:
        detail_parts = []
        seen_titles = set()
        for item in upcoming_items:
            title_key = item.get("title", "")[:40].lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            detail = _extract_upcoming_detail(item)
            detail_parts.append(detail)
        result["upcoming_details"] = " | ".join(detail_parts[:2])
        result["upcoming_summary"] = result["upcoming_details"]  # backward compat

    # Build content summary
    if result["season_name"]:
        content_parts.insert(0, result["season_name"])
    if result["new_content_details"]:
        content_parts.append(result["new_content_details"])
    if content_parts:
        result["content_summary"] = ", ".join(dict.fromkeys(content_parts))

    return result


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def scrape_all() -> list[dict]:
    """Scrape all game data: player counts, trends, news, reddit (week+month), comments."""
    results = []
    total = len(GAMES)

    for i, game in enumerate(GAMES, 1):
        name = game["name"]
        sub = game["subreddit"]
        print(f"  [{i}/{total}] {name}...")

        # SteamCharts
        data = get_steam_data(game)
        if not data:
            print(f"           players... FAILED")
            continue
        data["steam_share"] = game.get("steam_share", 1.0)
        data["genre"] = game.get("genre", "Other")
        print(f"           players... done")
        time.sleep(1)

        # Steam News (full content)
        news = get_steam_news(game["app_id"])
        data["news"] = news
        print(f"           news... {len(news)} items")
        time.sleep(1)

        # Reddit — weekly (near-term buzz)
        weekly_posts = get_reddit_posts(sub, timeframe="week", limit=5)
        print(f"           reddit/week... {len(weekly_posts)} posts")
        time.sleep(1)

        # Reddit — monthly (longer-term themes)
        monthly_posts = get_reddit_posts(sub, timeframe="month", limit=5)
        print(f"           reddit/month... {len(monthly_posts)} posts")
        time.sleep(1)

        # Comments on top 3 weekly posts
        for j, post in enumerate(weekly_posts[:3]):
            if post.get("permalink"):
                comments = get_reddit_comments(post["permalink"])
                weekly_posts[j]["top_comments"] = comments
                time.sleep(1)

        # Categorize reddit posts
        for post in weekly_posts:
            post["category"] = _categorize_post(post["title"], post.get("flair", ""), post.get("score", 0))
        for post in monthly_posts:
            post["category"] = _categorize_post(post["title"], post.get("flair", ""), post.get("score", 0))

        data["reddit_week"] = weekly_posts
        data["reddit_month"] = monthly_posts
        data["subreddit"] = sub

        # External press coverage (Google News RSS)
        ext_news = get_google_news_rss(name)
        data["external_news"] = ext_news
        print(f"           press... {len(ext_news)} articles")
        time.sleep(1)

        # Analyze developer comms
        data["dev_comms"] = _analyze_dev_comms(news)

        results.append(data)

        if i < total:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    return results


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def _enrich(results: list[dict]) -> list[dict]:
    results.sort(key=lambda x: x["peak_24h"], reverse=True)

    for rank, r in enumerate(results, 1):
        r["rank"] = rank
        r["pct_all"] = (
            (r["peak_24h"] / r["peak_all"] * 100) if r["peak_all"] > 0 else 0.0
        )

        months = r.get("months", [])
        if months and months[0].get("pct_gain") is not None:
            r["trend_pct"] = months[0]["pct_gain"]
        elif len(months) >= 2 and months[1].get("pct_gain") is not None:
            r["trend_pct"] = months[1]["pct_gain"]
        else:
            r["trend_pct"] = None

        arrow, css = _trend_arrow(r.get("trend_pct"))
        r["trend_arrow"] = arrow
        r["trend_css"] = css

        avg_trend = [m for m in months[:4] if m.get("avg") is not None]
        r["avg_trend"] = list(reversed(avg_trend))

        # Multi-period peaks (from monthly data)
        def _max_peak(month_slice):
            peaks = [m.get("peak") for m in month_slice if m.get("peak") is not None]
            return max(peaks) if peaks else None

        r["peak_30d"] = months[0].get("peak") if months else None
        r["peak_3m"] = _max_peak(months[:3])
        r["peak_6m"] = _max_peak(months[:6])

        # Platform mix: estimated total players across all platforms
        steam_share = r.get("steam_share", 1.0)
        r["steam_share"] = steam_share
        r["is_steam_only"] = steam_share >= 1.0
        if steam_share > 0:
            r["est_total_24h"] = int(r["peak_24h"] / steam_share)
            r["est_total_all"] = int(r["peak_all"] / steam_share)
        else:
            r["est_total_24h"] = r["peak_24h"]
            r["est_total_all"] = r["peak_all"]

    return results


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

def _save_history(results: list[dict], out_dir: str) -> None:
    history_dir = os.path.join(out_dir, "history")
    os.makedirs(history_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(history_dir, f"{date_str}.json")

    snapshot = {"date": date_str, "games": []}
    for r in results:
        snapshot["games"].append({
            "name": r["name"],
            "app_id": r["app_id"],
            "rank": r["rank"],
            "peak_24h": r["peak_24h"],
            "peak_all": r["peak_all"],
            "pct_all": r.get("pct_all"),
            "trend_pct": r.get("trend_pct"),
            "months": r.get("months", []),
            "news_titles": [n["title"] for n in r.get("news", [])],
            "reddit_week_top_score": (
                r["reddit_week"][0]["score"] if r.get("reddit_week") else None
            ),
            "takeaway": r.get("takeaway", ""),
            "steam_share": r.get("steam_share", 1.0),
            "est_total_24h": r.get("est_total_24h"),
        })

    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"  History saved: {path}")


def _load_previous_history(out_dir: str) -> dict | None:
    history_dir = os.path.join(out_dir, "history")
    if not os.path.isdir(history_dir):
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    files = sorted(
        [f for f in os.listdir(history_dir) if f.endswith(".json") and f[:-5] != today],
        reverse=True,
    )
    if not files:
        return None

    path = os.path.join(history_dir, files[0])
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    return {g["name"]: g for g in data.get("games", [])}


def _compute_deltas(results: list[dict], previous: dict | None) -> None:
    for r in results:
        if not previous:
            r["prev"] = None
            r["peak_24h_delta"] = None
            r["rank_delta"] = None
            continue

        prev = previous.get(r["name"])
        if not prev:
            r["prev"] = None
            r["peak_24h_delta"] = None
            r["rank_delta"] = None
            continue

        r["prev"] = {
            "rank": prev.get("rank"),
            "peak_24h": prev.get("peak_24h"),
            "trend_pct": prev.get("trend_pct"),
            "takeaway": prev.get("takeaway", ""),
        }
        r["peak_24h_delta"] = (
            r["peak_24h"] - prev["peak_24h"] if prev.get("peak_24h") else None
        )
        r["rank_delta"] = (
            prev["rank"] - r["rank"] if prev.get("rank") else None  # positive = moved up
        )


# ---------------------------------------------------------------------------
# Takeaway generation (template-based)
# ---------------------------------------------------------------------------

def _generate_game_takeaway(r: dict) -> dict:
    """Generate a structured 4-part takeaway for a game.

    Returns dict with keys: state, context, community, outlook (each a string).
    Also sets r["takeaway"] as a combined string for backward compatibility.
    """
    name = r["name"]
    dev = r.get("dev_comms", {})
    news = r.get("news", [])

    # === PART 1: CURRENT STATE ===
    state_parts = []
    trend_pct = r.get("trend_pct")
    if trend_pct is not None:
        # Current 30d avg
        avg_trend = r.get("avg_trend", [])
        current_avg = avg_trend[-1]["avg"] if avg_trend else None
        avg_str = f", averaging {_fmt_k(current_avg)} players over the last 30 days" if current_avg else ""

        if trend_pct > 10:
            state_parts.append(f"{name} is surging ({trend_pct:+.1f}% MoM{avg_str})")
        elif trend_pct > 2:
            state_parts.append(f"{name} is growing ({trend_pct:+.1f}% MoM{avg_str})")
        elif trend_pct > -2:
            state_parts.append(f"{name} is holding steady ({trend_pct:+.1f}%{avg_str})")
        elif trend_pct > -10:
            state_parts.append(f"{name} is declining ({trend_pct:+.1f}% MoM{avg_str})")
        else:
            state_parts.append(f"{name} is dropping sharply ({trend_pct:+.1f}% MoM{avg_str})")

        # Acceleration vs. previous run
        if r.get("prev") and r["prev"].get("trend_pct") is not None:
            prev_t = r["prev"]["trend_pct"]
            if trend_pct > prev_t + 5:
                state_parts[-1] += ", accelerating vs. last run"
            elif trend_pct < prev_t - 5:
                state_parts[-1] += ", decelerating vs. last run"

        state_parts[-1] += "."

    # Peak proximity
    pct_all = r.get("pct_all", 0)
    if pct_all > 70:
        state_parts.append(f"Currently at {pct_all:.0f}% of all-time peak — near historical highs.")
    elif pct_all < 15:
        state_parts.append(f"At just {pct_all:.0f}% of all-time peak — well below historical levels.")

    state = " ".join(state_parts) if state_parts else f"{name}: insufficient trend data."

    # === PART 2: CONTEXT (WHY — trend hypothesis) ===
    # Generate an AI hypothesis explaining what's driving the player trend
    hypothesis = _generate_trend_hypothesis(r)

    # Add developer activity details as supporting evidence
    context_parts = [hypothesis]

    # Supplement with specific dev activity facts
    activity_facts = []
    if dev.get("has_new_season"):
        season_str = dev.get("season_name", "a new season")
        content_detail = dev.get("new_content_details", "")
        if content_detail:
            activity_facts.append(f"{season_str} launched with {content_detail}")
        else:
            activity_facts.append(f"{season_str} launched recently")

    if dev.get("has_balance_changes") and dev.get("balance_details"):
        activity_facts.append(f"Balance changes to {dev['balance_details']}")

    if dev.get("has_bug_fixes") and dev.get("bug_fix_count", 0) > 3:
        activity_facts.append(f"{dev['bug_fix_count']}+ bug fixes deployed")

    if activity_facts:
        context_parts.append("Dev activity: " + "; ".join(activity_facts) + ".")

    context = " ".join(context_parts)

    # === PART 3: COMMUNITY & PRESS REACTION (synthesized) ===
    community_parts = []

    # Synthesize Reddit sentiment distribution — never quote raw titles
    weekly = r.get("reddit_week", [])
    monthly = r.get("reddit_month", [])
    all_posts = weekly + monthly
    substantive = [p for p in all_posts if p.get("category") in
                   {"NEWS", "CRITICISM", "DISCUSSION", "PRAISE"}]

    if substantive:
        cats = {}
        for p in substantive:
            cat = p.get("category", "OTHER")
            cats[cat] = cats.get(cat, 0) + 1

        total = len(substantive)
        top_cat = max(cats, key=cats.get)
        top_count = cats[top_cat]

        # Category human-readable descriptions
        cat_descriptions = {
            "NEWS": "game updates and announcements",
            "CRITICISM": "player frustrations and complaints",
            "PRAISE": "positive reception and appreciation",
            "DISCUSSION": "gameplay discussion and strategy",
        }

        if top_count >= total * 0.6 and total >= 3:
            # Dominant category
            cat_desc = cat_descriptions.get(top_cat, "general discussion")
            if top_cat == "CRITICISM":
                community_parts.append(
                    f"Community sentiment is strongly negative this week — "
                    f"{top_count} of {total} substantive posts focus on {cat_desc}."
                )
            elif top_cat == "PRAISE":
                community_parts.append(
                    f"Community sentiment is strongly positive — "
                    f"{top_count} of {total} substantive posts express {cat_desc}."
                )
            elif top_cat == "NEWS":
                community_parts.append(
                    f"Community discussion this week centers on {cat_desc} — "
                    f"{top_count} of {total} posts are news-focused."
                )
            else:
                community_parts.append(
                    f"Community is actively engaged in {cat_desc} — "
                    f"{top_count} of {total} posts this period."
                )
        elif total >= 2:
            # Mixed sentiment — show top two categories
            sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
            parts = []
            for cat, n in sorted_cats[:2]:
                desc = cat_descriptions.get(cat, cat.lower())
                parts.append(f"{desc} ({n} posts)")
            community_parts.append(
                f"Mixed community sentiment — discussion split between {' and '.join(parts)}."
            )
        elif total == 1:
            cat_desc = cat_descriptions.get(top_cat, "general discussion")
            community_parts.append(f"Limited community activity — one substantive post about {cat_desc}.")

    # Press coverage — synthesize topics from sources, not raw titles
    ext_news = r.get("external_news", [])
    if ext_news:
        sources = [a.get("source", "") for a in ext_news[:4] if a.get("source")]
        unique_sources = list(dict.fromkeys(sources))[:3]  # deduplicate, keep order

        if len(ext_news) >= 3:
            source_str = ", ".join(unique_sources) if unique_sources else "multiple outlets"
            community_parts.append(
                f"Active press coverage from {source_str} "
                f"({len(ext_news)} articles from gaming press in the past week)."
            )
        elif ext_news:
            source_str = unique_sources[0] if unique_sources else "press"
            community_parts.append(
                f"Press coverage from {source_str} "
                f"({len(ext_news)} {'article' if len(ext_news) == 1 else 'articles'} from gaming press in the past week)."
            )

    community = " ".join(community_parts) if community_parts else ""

    # === PART 4: OUTLOOK ===
    outlook_parts = []

    if dev.get("has_upcoming_event") and dev.get("upcoming_details"):
        outlook_parts.append(f"Looking ahead: {dev['upcoming_details']}")
    elif dev.get("has_upcoming_event") and dev.get("upcoming_summary"):
        outlook_parts.append(f"Looking ahead: {dev['upcoming_summary']}")

    # Historical trajectory
    if r.get("prev") and r["prev"].get("trend_pct") is not None:
        prev_t = r["prev"]["trend_pct"]
        if trend_pct is not None:
            if prev_t < -2 and trend_pct < -2:
                outlook_parts.append("Continued decline from last period — watch for content response.")
            elif prev_t > 2 and trend_pct > 2:
                outlook_parts.append("Sustained growth trajectory.")
            elif prev_t < -5 and trend_pct > 2:
                outlook_parts.append("Recovery signal — reversed previous decline.")

    outlook = " ".join(outlook_parts) if outlook_parts else ""

    # === BUILD STRUCTURED RESULT ===
    takeaway_dict = {
        "state": state,
        "context": context,
        "community": community,
        "outlook": outlook,
    }
    r["takeaway_structured"] = takeaway_dict

    # Combined string for backward compat + history
    combined_parts = [state, context]
    if community:
        combined_parts.append(community)
    if outlook:
        combined_parts.append(outlook)
    r["takeaway"] = " ".join(combined_parts)

    return takeaway_dict


def _generate_overall_takeaways(results: list[dict]) -> list[str]:
    """Generate concise executive summary bullets (no market direction — that's in the table)."""
    takeaways = []
    with_trend = [r for r in results if r.get("trend_pct") is not None]

    if not with_trend:
        return ["Insufficient trend data for market analysis."]

    # 1. Biggest mover up
    gainer = max(with_trend, key=lambda r: r["trend_pct"])
    if gainer["trend_pct"] > 5:
        takeaways.append(f"Biggest mover: {gainer['name']} at {gainer['trend_pct']:+.1f}% month-over-month.")

    # 2. Steepest decline
    loser = min(with_trend, key=lambda r: r["trend_pct"])
    if loser["trend_pct"] < -5:
        takeaways.append(f"Steepest decline: {loser['name']} at {loser['trend_pct']:+.1f}% month-over-month.")

    # 3. Run-over-run delta (compares 24h peaks to previous snapshot)
    prev_avail = [r for r in results if r.get("prev") and r["prev"].get("peak_24h")]
    if prev_avail:
        cur_total = sum(r["peak_24h"] for r in prev_avail)
        prev_total = sum(r["prev"]["peak_24h"] for r in prev_avail)
        if prev_total > 0:
            delta = (cur_total - prev_total) / prev_total * 100
            direction = "up" if delta > 0 else "down"
            takeaways.append(f"Combined 24h peaks across all 15 titles are {direction} {abs(delta):.1f}% vs. last week.")

    if not takeaways:
        takeaways.append(f"Tracking {len(results)} competitive shooter titles this week.")

    return takeaways


def _generate_winners_neutrals_losers(results: list[dict]) -> dict:
    """Categorize games into winners, neutrals, losers based on trend_pct.

    Returns dict with keys: winners, neutrals, losers — each a list of
    dicts: {name, trend_pct, trend_arrow, peak_24h}.
    """
    with_trend = [r for r in results if r.get("trend_pct") is not None]
    no_trend = [r for r in results if r.get("trend_pct") is None]

    winners = sorted(
        [r for r in with_trend if r["trend_pct"] > 2],
        key=lambda r: r["trend_pct"], reverse=True
    )
    losers = sorted(
        [r for r in with_trend if r["trend_pct"] < -2],
        key=lambda r: r["trend_pct"]
    )
    neutrals = sorted(
        [r for r in with_trend if -2 <= r["trend_pct"] <= 2],
        key=lambda r: abs(r["trend_pct"])
    )
    # Games with no trend data go into neutrals
    neutrals += no_trend

    def _extract(r):
        return {
            "name": r["name"],
            "trend_pct": r.get("trend_pct"),
            "trend_arrow": r.get("trend_arrow", "?"),
            "peak_24h": r["peak_24h"],
        }

    return {
        "winners": [_extract(r) for r in winners],
        "neutrals": [_extract(r) for r in neutrals],
        "losers": [_extract(r) for r in losers],
    }


# ---------------------------------------------------------------------------
# Release & Patch Calendar
# ---------------------------------------------------------------------------

# Curated industry-wide shooter release calendar.
# Sources: IGN, GameSpot, PC Gamer, Game Informer, Insider Gaming release calendars.
# Update this list as new dates are announced — it changes slowly.
# Last updated: 2026-02-16
INDUSTRY_RELEASES = [
    # Confirmed dates — sourced from IGN, GameSpot, PC Gamer release calendars
    # Last verified: 2026-02-17 against https://www.ign.com/articles/video-game-release-dates
    {"game": "Marathon", "date": "2026-03-05", "type": "New Release",
     "desc": "Bungie's extraction shooter reboot. PC/PS5/Xbox. Cross-play, $40.",
     "confirmed": True},
    {"game": "John Carpenter's Toxic Commando", "date": "2026-03-12", "type": "New Release",
     "desc": "Co-op zombie FPS. Saber Interactive. PC/PS5/Xbox.",
     "confirmed": True},
    {"game": "Mouse: P.I. for Hire", "date": "2026-03-19", "type": "New Release",
     "desc": "Noir-themed retro FPS. PC/PS5/Switch/Xbox.",
     "confirmed": True},
    {"game": "007 First Light", "date": "2026-05-27", "type": "New Release",
     "desc": "IO Interactive (Hitman devs) James Bond origin story. Third-person action-shooter. PC/PS5/Xbox/Switch 2.",
     "confirmed": True},
    {"game": "Halloween: The Game", "date": "2026-09-08", "type": "New Release",
     "desc": "Horror shooter based on the film franchise. PC/PS5/Xbox.",
     "confirmed": True},
    # Confirmed 2026, month estimated
    {"game": "Halo: Campaign Evolved", "date": "2026-06-15", "type": "New Release",
     "desc": "Full remake of Halo: Combat Evolved, rebuilt from the ground up. PC/PS5/Xbox. Targeting Summer 2026.",
     "confirmed": False},
    {"game": "Warhammer 40K: Boltgun 2", "date": "2026-06-01", "type": "New Release",
     "desc": "Retro-style FPS sequel. Auroch Digital. PC/PS5/Xbox. Targeting 2026.",
     "confirmed": False},
    {"game": "Turok Origins", "date": "2026-10-01", "type": "New Release",
     "desc": "FPS franchise revival/reboot. PC/PS5/Switch 2/Xbox. Targeting Fall 2026.",
     "confirmed": False},
    {"game": "Hell Let Loose: Vietnam", "date": "2026-09-01", "type": "New Release",
     "desc": "50v50 multiplayer set in Vietnam. Sequel to Hell Let Loose. PC/PS5/Xbox. Targeting 2026.",
     "confirmed": False},
    {"game": "Gears of War: E-Day", "date": "2026-11-15", "type": "New Release",
     "desc": "Prequel to the original Gears of War. The Coalition + People Can Fly. PC/Xbox. TBA per IGN.",
     "confirmed": False},
    {"game": "Borderlands 4", "date": "2026-09-15", "type": "New Release",
     "desc": "Looter-shooter FPS sequel. Gearbox Software. Multi-platform. Targeting 2026.",
     "confirmed": False},
    {"game": "Judas", "date": "2026-12-01", "type": "New Release",
     "desc": "FPS from Ken Levine (BioShock creator). Ghost Story Games. PC/PS5/Xbox. TBA per IGN.",
     "confirmed": False},
]


def _classify_event_type(title: str, is_patch: bool = False) -> str:
    """Classify a news item into an event type for the calendar."""
    t = title.lower()
    if is_patch or "patch" in t or "hotfix" in t or "fix" in t:
        return "Patch"
    if "season" in t or "new season" in t:
        return "Season"
    if "event" in t or "limited" in t or "ltm" in t or "celebration" in t:
        return "Event"
    if "roadmap" in t or "road ahead" in t or "year" in t:
        return "Roadmap"
    return "Content"


def _event_importance(title: str, is_patch: bool = False) -> int:
    """Rate event importance: 1=must show, 2=show if space, 3=skip.

    Tier 1 (always show): Season launches, major expansions, roadmaps, new game modes
    Tier 2 (show if space): Mid-season updates with new content, ranked resets, events
    Tier 3 (never show): Routine patches, localization, ban waves, skin drops, blog posts
    """
    t = title.lower()

    # Tier 3 — noise to filter out
    tier3_kw = re.compile(
        r'\b(?:localization|ban notice|bans notice|weekly bans|'
        r'mod minute|community hub|blog|newsletter|minor|'
        r'appearance|cosmetic|skin release|bundle|store|shop)\b', re.I
    )
    if tier3_kw.search(t):
        return 3
    if is_patch and not any(kw in t for kw in ["major", "season", "update", "new map", "new mode", "new hero", "new agent"]):
        # Generic patches without noteworthy keywords
        if re.search(r'^\s*\S+\s+update\s*$', t, re.I) or "hotfix" in t:
            return 3

    # Tier 1 — high importance
    tier1_kw = re.compile(
        r'\b(?:season\s+\d|new season|season launch|roadmap|road ahead|'
        r'expansion|new map|new hero|new agent|new legend|new operator|'
        r'new mode|launch|release|early access|open beta|year \d|'
        r'expedition|major update|anniversary|championship)\b', re.I
    )
    if tier1_kw.search(t):
        return 1

    # Tier 2 — moderate
    return 2


_FUTURE_DATE_RE = re.compile(
    r'(?:(?:on|from|begins?|launches?|starting|available)\s+)?'
    r'((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)',
    re.I
)


def _extract_future_dates(text: str, current_year: int) -> list[tuple[str, datetime]]:
    """Extract all date references from text and return as (original_str, datetime) pairs."""
    results = []
    for m in _FUTURE_DATE_RE.finditer(text):
        raw = m.group(1).strip()
        # Remove ordinal suffixes
        cleaned = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', raw)
        # Try parsing with year, then without
        parsed = False
        for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"]:
            try:
                dt = datetime.strptime(cleaned, fmt)
                results.append((raw, dt))
                parsed = True
                break
            except ValueError:
                continue
        if not parsed:
            # No year in string — append current_year to avoid deprecation
            for fmt in ["%B %d", "%b %d"]:
                try:
                    dt = datetime.strptime(f"{cleaned} {current_year}", f"{fmt} %Y")
                    results.append((raw, dt))
                    break
                except ValueError:
                    continue
    return results


def _build_release_calendar(results: list[dict]) -> dict:
    """Build a curated, forward-looking release calendar.

    Returns dict with keys:
      "this_week": [entries for the last 7 days — curated, 1 per game max]
      "coming_up": [entries in the next 14 days — confirmed dates only]
      "months": OrderedDict {"March 2026": [entries], ...} for next 5 months
      "estimated": [estimated entries for future months from cadence patterns]

    Each entry: {"game", "type", "date_str", "date_dt", "desc", "url", "estimated"}
    """
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - __import__('datetime').timedelta(days=7)
    two_weeks_ahead = today + __import__('datetime').timedelta(days=14)
    current_year = now.year

    # Build month buckets for the next 5 months (exclude current month — handled by this_week/coming_up)
    from collections import OrderedDict
    future_months = OrderedDict()
    for offset in range(1, 11):  # 10 months ahead — cover through end of year
        m = now.month + offset
        y = now.year
        if m > 12:
            m -= 12
            y += 1
        dt = datetime(y, m, 1)
        future_months[dt.strftime("%B %Y")] = []

    this_week = []    # past 7 days, curated
    coming_up = []    # next 14 days, confirmed
    all_raw = []      # everything before filtering

    for r in results:
        game_name = r["name"]

        # --- Source 1: Steam News (patches, seasons, events) ---
        for n in r.get("news", []):
            date_str = n.get("date", "")
            title = n.get("title", "")
            importance = _event_importance(title, n.get("is_patch", False))
            if importance >= 3:
                continue  # Skip noise

            event_type = _classify_event_type(title, n.get("is_patch", False))
            desc = _sanitize_text(title)

            # Parse event publication date
            event_dt = None
            if date_str:
                try:
                    event_dt = datetime.strptime(f"{date_str} {current_year}", "%b %d %Y")
                except ValueError:
                    pass

            entry = {
                "game": game_name,
                "type": event_type,
                "date_str": date_str or "Recent",
                "date_dt": event_dt,
                "desc": desc,
                "url": n.get("url", ""),
                "estimated": False,
                "importance": importance,
            }
            all_raw.append(entry)

            # Also scan article content for future dates mentioned
            contents = n.get("contents", "")
            if contents:
                future_refs = _extract_future_dates(contents, current_year)
                for raw_date_str, future_dt in future_refs:
                    if future_dt > today:
                        month_key = future_dt.strftime("%B %Y")
                        if month_key in future_months:
                            all_raw.append({
                                "game": game_name,
                                "type": event_type,
                                "date_str": future_dt.strftime("%b %d"),
                                "date_dt": future_dt,
                                "desc": f"{desc} (mentioned: {raw_date_str})",
                                "url": n.get("url", ""),
                                "estimated": False,
                                "importance": importance,
                            })

        # --- Source 2: dev_comms upcoming events ---
        dev = r.get("dev_comms", {})
        if dev.get("has_upcoming_event") and dev.get("upcoming_details"):
            detail = _sanitize_text(dev["upcoming_details"][:200])
            importance = _event_importance(detail)
            if importance < 3:
                # Extract all dates from the upcoming detail text
                future_refs = _extract_future_dates(detail, current_year)
                if future_refs:
                    for raw_date_str, future_dt in future_refs:
                        month_key = future_dt.strftime("%B %Y")
                        target = future_months if month_key in future_months else None
                        all_raw.append({
                            "game": game_name,
                            "type": _classify_event_type(detail),
                            "date_str": future_dt.strftime("%b %d"),
                            "date_dt": future_dt,
                            "desc": detail,
                            "url": "",
                            "estimated": False,
                            "importance": importance,
                        })

    # --- Deduplicate: keep only the most important entry per game per event ---
    def _dedup_key(e):
        """Group entries that are about the same event."""
        # Normalize: strip numbers, lowercase, first 30 chars
        norm = re.sub(r'\d+', '', e["desc"].lower())[:30].strip()
        return (e["game"], norm)

    seen = {}
    deduped = []
    for e in sorted(all_raw, key=lambda x: x["importance"]):
        key = _dedup_key(e)
        if key not in seen:
            seen[key] = True
            deduped.append(e)

    # --- Bucket into this_week / coming_up / future months ---
    for e in deduped:
        dt = e.get("date_dt")
        if dt is None:
            continue

        if week_ago <= dt <= today:
            this_week.append(e)
        elif today < dt <= two_weeks_ahead:
            coming_up.append(e)
        else:
            month_key = dt.strftime("%B %Y")
            if month_key in future_months:
                future_months[month_key].append(e)

    # --- Limit this_week to max 1 entry per game (highest importance) ---
    tw_by_game = {}
    for e in sorted(this_week, key=lambda x: x["importance"]):
        if e["game"] not in tw_by_game:
            tw_by_game[e["game"]] = e
    this_week = sorted(tw_by_game.values(), key=lambda x: x["date_dt"] or today)

    # Sort coming_up by date
    coming_up.sort(key=lambda x: x["date_dt"] or today)

    # Sort future month entries by date
    for month_key in future_months:
        future_months[month_key].sort(key=lambda x: x["date_dt"] or today)

    # --- Seasonal cadence estimates for empty future months ---
    # Known cadences: approximate weeks between seasons
    CADENCES = {
        "Call of Duty": {"label": "Season", "weeks": 8},
        "Marvel Rivals": {"label": "Season", "weeks": 8},
        "Apex Legends": {"label": "Season", "weeks": 13},
        "Overwatch": {"label": "Season", "weeks": 13},
        "Battlefield 6": {"label": "Season", "weeks": 13},
        "Delta Force": {"label": "Season", "weeks": 10},
        "Rainbow Six Siege": {"label": "Season", "weeks": 13},
        "Destiny 2": {"label": "Season", "weeks": 13},
        "The Finals": {"label": "Season", "weeks": 10},
        "PUBG: BATTLEGROUNDS": {"label": "Content update", "weeks": 8},
    }

    # Find the most recent season/content launch per game from this_week + coming_up + all data
    last_major = {}
    for e in deduped:
        if e["date_dt"] and e["importance"] == 1 and e["type"] in ("Season", "Content", "Event"):
            game = e["game"]
            if game not in last_major or (e["date_dt"] and e["date_dt"] > last_major[game]["date_dt"]):
                last_major[game] = e

    estimated = []
    for game_name, cadence in CADENCES.items():
        if game_name not in last_major:
            continue
        last_dt = last_major[game_name]["date_dt"]
        if not last_dt:
            continue
        weeks = cadence["weeks"]
        label = cadence["label"]

        # Project next event(s)
        from datetime import timedelta
        next_dt = last_dt + timedelta(weeks=weeks)
        # Generate up to 2 projected events
        for _ in range(2):
            if next_dt <= today:
                next_dt += timedelta(weeks=weeks)
                continue
            month_key = next_dt.strftime("%B %Y")
            if month_key in future_months:
                # Only add if no confirmed entry for this game in that month
                existing_games = {e["game"] for e in future_months[month_key]}
                if game_name not in existing_games:
                    est_entry = {
                        "game": game_name,
                        "type": label,
                        "date_str": f"~{next_dt.strftime('%b')}",
                        "date_dt": next_dt,
                        "desc": f"Next {label.lower()} expected (based on ~{weeks}-week cadence)",
                        "url": "",
                        "estimated": True,
                        "importance": 2,
                    }
                    estimated.append(est_entry)
                    future_months[month_key].append(est_entry)
            next_dt += timedelta(weeks=weeks)

    # --- Industry-wide new game releases ---
    for rel in INDUSTRY_RELEASES:
        try:
            rel_dt = datetime.strptime(rel["date"], "%Y-%m-%d")
        except ValueError:
            continue

        entry = {
            "game": rel["game"],
            "type": rel["type"],
            "date_str": rel_dt.strftime("%b %d") if rel["confirmed"] else f"~{rel_dt.strftime('%b')}",
            "date_dt": rel_dt,
            "desc": rel["desc"],
            "url": "",
            "estimated": not rel["confirmed"],
            "importance": 1,  # New game releases are always high importance
        }

        if week_ago <= rel_dt <= today:
            this_week.append(entry)
        elif today < rel_dt <= two_weeks_ahead:
            coming_up.append(entry)
        else:
            month_key = rel_dt.strftime("%B %Y")
            if month_key in future_months:
                future_months[month_key].append(entry)

    # Re-sort after adding industry releases
    this_week.sort(key=lambda x: x.get("date_dt") or today)
    coming_up.sort(key=lambda x: x.get("date_dt") or today)
    for mk in future_months:
        future_months[mk].sort(key=lambda x: x.get("date_dt") or today)

    # Add industry calendar notes for summer months
    for month_key in future_months:
        if "June" in month_key or "July" in month_key:
            has_note = any(e.get("type") == "Industry" for e in future_months[month_key])
            if not has_note:
                future_months[month_key].append({
                    "game": "Industry",
                    "type": "Industry",
                    "date_str": month_key.split()[0][:3],
                    "date_dt": None,
                    "desc": "Summer Game Fest window — expect major shooter reveals and announcements",
                    "url": "",
                    "estimated": True,
                    "importance": 1,
                })

    return {
        "this_week": this_week,
        "coming_up": coming_up,
        "months": future_months,
        "estimated": estimated,
    }


EVENT_TYPE_CSS = {
    "Season": "season",
    "Patch": "patch",
    "Event": "event",
    "Content": "content",
    "Roadmap": "roadmap",
    "Industry": "industry",
    "New Release": "newrelease",
}


def _render_cal_entry_html(e: dict) -> str:
    """Render a single calendar entry as HTML."""
    type_class = EVENT_TYPE_CSS.get(e["type"], "content")
    url = e.get("url", "")
    desc_text = _esc(e.get("desc", ""))
    if url:
        desc_text = f'<a href="{_esc(url)}" target="_blank" class="item-link">{desc_text}</a>'
    estimated_class = " estimated" if e.get("estimated") else ""
    estimated_tag = ' <span class="est-tag">ESTIMATED</span>' if e.get("estimated") else ""
    return f'''      <div class="cal-entry{estimated_class}">
        <span class="cal-date">{_esc(e.get("date_str", ""))}</span>
        <span class="cal-game">{_esc(e["game"])}</span>
        <span class="calendar-type {type_class}">{_esc(e["type"])}</span>
        <span class="cal-desc">{desc_text}{estimated_tag}</span>
      </div>'''


def _render_calendar_html(cal_data: dict) -> str:
    """Render the curated release calendar: This Week / Coming Up / Future Months."""
    this_week = cal_data.get("this_week", [])
    coming_up = cal_data.get("coming_up", [])
    future_months = cal_data.get("months", {})

    has_content = this_week or coming_up or any(future_months.values())
    if not has_content:
        return ""

    # --- This Week section ---
    tw_html = ""
    if this_week:
        entries = "\n".join(_render_cal_entry_html(e) for e in this_week)
        tw_html = f'''    <div class="cal-section">
      <h3 class="cal-section-header past">This Week</h3>
{entries}
    </div>\n'''
    else:
        tw_html = '''    <div class="cal-section">
      <h3 class="cal-section-header past">This Week</h3>
      <div class="cal-empty">No major events tracked this week.</div>
    </div>\n'''

    # --- TODAY divider ---
    today_str = datetime.now().strftime("%b %d")
    today_divider = f'''    <div class="cal-today-divider">
      <span>TODAY — {today_str}</span>
    </div>\n'''

    # --- Coming Up section ---
    cu_html = ""
    if coming_up:
        entries = "\n".join(_render_cal_entry_html(e) for e in coming_up)
        cu_html = f'''    <div class="cal-section">
      <h3 class="cal-section-header upcoming">Coming Up (Next 2 Weeks)</h3>
{entries}
    </div>\n'''
    else:
        cu_html = '''    <div class="cal-section">
      <h3 class="cal-section-header upcoming">Coming Up (Next 2 Weeks)</h3>
      <div class="cal-empty">No confirmed events in the next 2 weeks.</div>
    </div>\n'''

    # --- Future months ---
    months_html = ""
    for month_name, entries in future_months.items():
        if entries:
            confirmed = [e for e in entries if not e.get("estimated")]
            estimated = [e for e in entries if e.get("estimated")]
            all_entries = confirmed + estimated
            entries_html = "\n".join(_render_cal_entry_html(e) for e in all_entries)
            count_note = ""
            if confirmed and estimated:
                count_note = f' <span class="cal-count">{len(confirmed)} confirmed, {len(estimated)} estimated</span>'
            elif estimated:
                count_note = f' <span class="cal-count">{len(estimated)} estimated</span>'
            months_html += f'''    <div class="cal-section">
      <h3 class="cal-section-header future">{_esc(month_name)}{count_note}</h3>
{entries_html}
    </div>\n'''
        else:
            months_html += f'''    <div class="cal-section">
      <h3 class="cal-section-header future">{_esc(month_name)}</h3>
      <div class="cal-empty">No tracked events yet — check back as announcements come in.</div>
    </div>\n'''

    return f'''  <div class="calendar-section">
    <h2 class="section-title">Release &amp; Patch Calendar</h2>
{tw_html}
{today_divider}
{cu_html}
{months_html}  </div>'''


# ---------------------------------------------------------------------------
# Studio Alert for Halo titles (#3)
# ---------------------------------------------------------------------------

def _build_studio_alert_html(results: list[dict], date_str: str) -> str:
    halo_inf = next((r for r in results if r["name"] == "Halo Infinite"), None)
    halo_mcc = next((r for r in results if r["name"] == "Halo: MCC"), None)
    if not halo_inf and not halo_mcc:
        return ""

    # Determine status color
    inf_declining = halo_inf and (halo_inf.get("trend_pct") or 0) < -2
    mcc_declining = halo_mcc and (halo_mcc.get("trend_pct") or 0) < -2
    if inf_declining and mcc_declining:
        status_color = "#f87171"
        status_emoji = "\U0001f534"
        border_color = "#f87171"
    elif inf_declining or mcc_declining:
        status_color = "#fbbf24"
        status_emoji = "\U0001f7e1"
        border_color = "#fbbf24"
    else:
        status_color = "#4ade80"
        status_emoji = "\U0001f7e2"
        border_color = "#4ade80"

    def _halo_line(r, lifecycle_note):
        if not r:
            return ""
        trend = f"{r.get('trend_pct', 0):+.1f}%" if r.get("trend_pct") is not None else "N/A"
        return (
            f'<div class="studio-alert-game">'
            f'<strong>{_esc(r["name"])}</strong>: '
            f'#{r["rank"]}/15 &nbsp;|&nbsp; '
            f'{_fmt(r["peak_24h"])} Steam (est. {_fmt(r.get("est_total_24h", r["peak_24h"]))} all platforms) &nbsp;|&nbsp; '
            f'{r["pct_all"]:.1f}% of ATH &nbsp;|&nbsp; '
            f'<span class="trend {r.get("trend_css", "neutral")}">{trend} MoM</span>'
            f'<div class="studio-alert-lifecycle">\u2514 Lifecycle: {lifecycle_note}</div>'
            f'</div>'
        )

    lines = ""
    if halo_inf:
        lines += _halo_line(halo_inf, "Post-final update (Nov 2025). Managed sunset \u2192 Campaign Evolved (Summer 2026).")
    if halo_mcc:
        lines += _halo_line(halo_mcc, "Legacy title. Community-driven content only.")

    # Check for Marathon in calendar (within 30 days)
    marathon_note = ""
    for r in results:
        for n in r.get("news", []):
            if "marathon" in n.get("title", "").lower():
                marathon_note = '<div class="studio-alert-marathon">\u26a0\ufe0f Marathon (Bungie) launches soon \u2014 HIGH overlap with Halo\'s lapsed audience.</div>'
                break
        if marathon_note:
            break

    return f'''  <div class="studio-alert" style="border-left-color:{border_color}">
    <div class="studio-alert-header" style="color:{status_color}">{status_emoji} STUDIO ALERT \u2014 Week of {date_str}</div>
{lines}{marathon_note}  </div>'''


# ---------------------------------------------------------------------------
# Genre Rollup table (#9)
# ---------------------------------------------------------------------------

def _build_genre_rollup_html(results: list[dict]) -> str:
    from collections import defaultdict
    genre_data = defaultdict(lambda: {"games": [], "total_est": 0, "weighted_trend": 0, "trend_weight": 0})

    for r in results:
        g = r.get("genre", "Other")
        est = r.get("est_total_24h", r["peak_24h"])
        trend = r.get("trend_pct") or 0
        genre_data[g]["games"].append(r)
        genre_data[g]["total_est"] += est
        genre_data[g]["weighted_trend"] += trend * est
        genre_data[g]["trend_weight"] += est

    # Sort by total estimated players descending
    sorted_genres = sorted(genre_data.items(), key=lambda x: x[1]["total_est"], reverse=True)

    rows = ""
    for genre, data in sorted_genres:
        avg_trend = data["weighted_trend"] / data["trend_weight"] if data["trend_weight"] else 0
        dominant = max(data["games"], key=lambda r: r.get("est_total_24h", r["peak_24h"]))
        trend_css = "up" if avg_trend > 2 else ("down" if avg_trend < -2 else "flat")
        fg, bg = GENRE_COLORS.get(genre, GENRE_COLORS["Other"])
        rows += (
            f'<tr>'
            f'<td><span class="genre-badge" style="color:{fg};background:{bg}">{GENRE_SHORT.get(genre, genre)}</span></td>'
            f'<td class="num" style="color:#60a5fa;font-weight:600">{_fmt(data["total_est"])}</td>'
            f'<td class="trend {trend_css}" style="text-align:center">{avg_trend:+.1f}%</td>'
            f'<td>{_esc(dominant["name"])}</td>'
            f'<td style="text-align:center">{len(data["games"])}</td>'
            f'</tr>\n'
        )

    return f'''  <div class="genre-rollup">
    <h3>Genre Rollup</h3>
    <table>
      <thead><tr>
        <th>Genre</th>
        <th style="text-align:right">Combined Est. Daily Players</th>
        <th style="text-align:center">MoM Trend</th>
        <th>Dominant Title</th>
        <th style="text-align:center"># Titles</th>
      </tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
  </div>'''


# ---------------------------------------------------------------------------
# Methodology section (#7)
# ---------------------------------------------------------------------------

def _build_methodology_html(results: list[dict]) -> str:
    rows = ""
    for r in sorted(results, key=lambda x: x["rank"]):
        steam_share = r.get("steam_share", 1.0)
        multiplier = f"{1/steam_share:.1f}x" if steam_share > 0 else "N/A"
        note = PLATFORM_NOTES.get(r["name"], "")
        rows += (
            f'<tr>'
            f'<td>{_esc(r["name"])}</td>'
            f'<td class="num">{_fmt(r["peak_24h"])}</td>'
            f'<td style="text-align:center">{multiplier}</td>'
            f'<td class="num" style="color:#60a5fa">{_fmt(r.get("est_total_24h", r["peak_24h"]))}</td>'
            f'<td class="meth-note">{_esc(note)}</td>'
            f'</tr>\n'
        )

    return f'''  <div class="methodology" id="methodology">
    <details>
      <summary>Methodology &mdash; Platform Multipliers &amp; Data Sources</summary>
      <div class="methodology-content">
        <p class="methodology-disclaimer">All-platform estimates apply per-game multipliers based on platform mix models.
These are estimates, not validated against first-party data. Sources include publisher earnings reports,
analytics firms (Alinea, Newzoo), and community trackers.</p>
        <table>
          <thead><tr>
            <th>Game</th>
            <th style="text-align:right">Steam 24h Peak</th>
            <th style="text-align:center">Multiplier</th>
            <th style="text-align:right">Est. All Platforms</th>
            <th>Source / Notes</th>
          </tr></thead>
          <tbody>
{rows}          </tbody>
        </table>
      </div>
    </details>
  </div>'''


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(results: list[dict], failed_names: list[str],
                  overall_takeaways: list[str]) -> str:
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    timestamp = today.strftime("%Y-%m-%d %H:%M:%S")

    # --- Executive Summary with Winners / Neutrals / Losers ---
    exec_items = "\n".join(f"      <li>{_esc(_sanitize_text(t))}</li>" for t in overall_takeaways)
    aggregate_chart = _generate_aggregate_sparkline(results)
    wnl = _generate_winners_neutrals_losers(results)

    # Build winners / neutrals / losers mini-table
    def _wnl_rows(items, color, arrow_class):
        if not items:
            return f'<tr><td colspan="3" style="color:#556b7d;font-style:italic;padding:0.25rem 0.5rem;font-size:0.8rem">None</td></tr>'
        rows = ""
        for g in items:
            t = g["trend_pct"]
            t_str = f'{t:+.1f}%' if t is not None else "—"
            rows += (
                f'<tr>'
                f'<td style="color:#e5e5e5;font-weight:600;padding:0.2rem 0.5rem;font-size:0.82rem">{_esc(g["name"])}</td>'
                f'<td style="text-align:right;padding:0.2rem 0.5rem;font-size:0.82rem;color:{color};font-weight:600">{t_str}</td>'
                f'<td style="text-align:right;padding:0.2rem 0.5rem;font-size:0.82rem;color:#8f98a0">{_fmt(g["peak_24h"])}<div style="font-size:0.55rem;color:#556b7d;font-weight:400">Steam 24h</div></td>'
                f'</tr>'
            )
        return rows

    wnl_html = f"""    <div class="wnl-table">
      <div class="wnl-col">
        <div class="wnl-header" style="color:#4ade80;border-bottom:2px solid #4ade80">&#9650; Winners ({len(wnl['winners'])})</div>
        <table>{_wnl_rows(wnl['winners'], '#4ade80', 'up')}</table>
      </div>
      <div class="wnl-col">
        <div class="wnl-header" style="color:#fbbf24;border-bottom:2px solid #fbbf24">&#9654; Holding Steady ({len(wnl['neutrals'])})</div>
        <table>{_wnl_rows(wnl['neutrals'], '#fbbf24', 'flat')}</table>
      </div>
      <div class="wnl-col">
        <div class="wnl-header" style="color:#f87171;border-bottom:2px solid #f87171">&#9660; Losers ({len(wnl['losers'])})</div>
        <table>{_wnl_rows(wnl['losers'], '#f87171', 'down')}</table>
      </div>
    </div>"""

    exec_html = f"""  <div class="exec-summary">
    <h2>Executive Summary</h2>
    <ul>
{exec_items}
    </ul>
{wnl_html}
    {aggregate_chart}
  </div>"""

    # --- Genre filter tabs ---
    from collections import Counter
    genre_counts = Counter(r.get("genre", "Other") for r in results)
    # Ordered list: keep a consistent order
    genre_order = ["Battle Royale", "Hero Shooter", "Arena", "Tactical", "Extraction", "Large-Scale", "Looter Shooter", "Other"]
    genre_btns = '    <button class="genre-filter-btn active" data-genre="All">All <span class="filter-count">{}</span></button>\n'.format(len(results))
    for g in genre_order:
        if g in genre_counts:
            fg, bg = GENRE_COLORS.get(g, GENRE_COLORS["Other"])
            genre_btns += f'    <button class="genre-filter-btn" data-genre="{g}" style="--genre-active-bg:{bg};--genre-active-border:{fg};--genre-active-color:{fg}">{g} <span class="filter-count">{genre_counts[g]}</span></button>\n'
    genre_tabs_html = f'  <div class="genre-filters">\n{genre_btns}  </div>'

    # --- Genre Rollup (#9) ---
    genre_rollup_html = _build_genre_rollup_html(results)

    # --- Methodology (#7) ---
    methodology_html = _build_methodology_html(results)

    # --- Summary table rows ---
    table_rows = ""
    for r in results:
        trend_pct = r.get("trend_pct")
        trend_str = f"{trend_pct:+.1f}%" if trend_pct is not None else "?"
        bar_w = min(r["pct_all"], 100)

        est_total = _fmt(r.get('est_total_24h', r['peak_24h']))
        est_all_time = _fmt(r.get('est_total_all', r['peak_all']))

        genre = r.get('genre', 'Other')
        trend_val = trend_pct if trend_pct is not None else 0

        # Lifecycle badge (#4)
        lifecycle = _lifecycle_badge_html(r['name'])

        # Sentiment (#5)
        game_sentiment = _compute_game_sentiment(r)
        sent_color = {"positive": "#4ade80", "negative": "#f87171", "mixed": "#fbbf24"}.get(game_sentiment, "#94a3b8")
        sent_val = {"positive": 1, "mixed": 0, "negative": -1}.get(game_sentiment, 0)

        # Inline sparkline (#6)
        mini_spark = _inline_sparkline_svg(r.get("avg_trend", []), r.get("trend_css", "neutral"))

        # Event annotation (#8) — shown as tooltip on trend value
        annotation = EVENT_ANNOTATIONS.get(r['name'], "")
        trend_title = f' title="{_esc(annotation)}"' if annotation and abs(trend_val) > 9 else ""
        annotation_icon = ' <span class="annot-icon" title="' + _esc(annotation) + '">&#9432;</span>' if annotation and abs(trend_val) > 9 else ""

        # Sentiment dot merged into game name cell
        sent_dot = f' <span class="sent-inline" style="color:{sent_color}" title="Sentiment: {game_sentiment}">\u25cf</span>'

        table_rows += f"""        <tr data-genre="{genre}">
          <td class="rank" data-value="{r['rank']}">#{r['rank']}</td>
          <td class="game" data-value="{sent_val}">{_esc(r['name'])}{lifecycle}{sent_dot}</td>
          <td>{_genre_badge_html(genre)}</td>
          <td class="num" data-value="{r['peak_24h']}">{_fmt(r['peak_24h'])}</td>
          <td class="num" data-value="{r.get('est_total_24h', r['peak_24h'])}" style="color:#60a5fa;font-weight:600">{est_total}</td>
          <td class="trend {r['trend_css']}" data-value="{trend_val}"{trend_title}>{r['trend_arrow']} {trend_str} {mini_spark}{annotation_icon}</td>
          <td class="num" data-value="{r.get('est_total_all', r['peak_all'])}" style="color:#fbbf24;font-weight:600">{est_all_time}</td>
          <td class="pct-cell" data-value="{r['pct_all']:.2f}">
            <div class="bar-bg"><div class="bar" style="width:{bar_w}%"></div></div>
            <span>{r['pct_all']:.1f}%</span>
          </td>
        </tr>\n"""

    for name in failed_names:
        table_rows += f"""        <tr class="failed">
          <td class="rank">-</td>
          <td class="game">{_esc(name)}</td>
          <td>-</td>
          <td class="num">-</td><td class="num">-</td>
          <td class="trend neutral">-</td>
          <td class="num">-</td><td class="pct-cell">-</td>
        </tr>\n"""

    # --- Detail cards ---
    cards_html = ""
    for r in results:
        # SVG sparkline chart
        sparkline = _generate_sparkline_svg(r.get("avg_trend", []), r.get("trend_css", "neutral"))

        # News items with AI-extracted summary + sentiment dot + clickable links
        news_html = ""
        for n in r.get("news", [])[:3]:
            title_text = _esc(_sanitize_text(n["title"][:80]))
            news_url = n.get("url", "")
            if news_url:
                title = f'<a href="{_esc(news_url)}" target="_blank" class="item-link">{title_text}</a>'
            else:
                title = title_text
            badge = ' <span class="badge patch">PATCH</span>' if n["is_patch"] else ""
            sentiment = _analyze_sentiment(n.get("title", "") + " " + (n.get("contents", "") or "")[:200])
            s_fg, _ = _sentiment_css(sentiment)
            sent_dot = f'<span class="sentiment-dot" style="color:{s_fg}" title="{sentiment}">\u25cf</span> '
            summary = _extract_news_summary(n)
            summary_div = f'<div class="news-preview">{_esc(_sanitize_text(summary))}</div>' if summary else ""
            news_html += f'<li>{sent_dot}{title} \u2014 {n["date"]}{badge}{summary_div}</li>\n'
        if not news_html:
            news_html = "<li>No recent news</li>\n"

        # External press coverage — sentiment-colored source tags + clickable links
        press_html = ""
        for a in r.get("external_news", [])[:4]:
            title_text = _esc(_sanitize_text(a["title"][:75]))
            press_url = a.get("url", "")
            if press_url:
                title = f'<a href="{_esc(press_url)}" target="_blank" class="item-link">{title_text}</a>'
            else:
                title = title_text
            source = _esc(a.get("source", ""))
            date = _esc(a.get("date", ""))
            sentiment = _analyze_sentiment(a.get("title", ""))
            s_fg, s_bg = _sentiment_css(sentiment)
            source_badge = f' <span class="source-tag" style="color:{s_fg};background:{s_bg}">{source}</span>' if source else ""
            sent_dot = f'<span class="sentiment-dot" style="color:{s_fg}" title="{sentiment}">\u25cf</span> '
            date_span = f' <span style="color:#8f98a0;font-size:0.7rem">{date}</span>' if date else ""
            press_html += f'<li>{sent_dot}{title}{source_badge}{date_span}</li>\n'
        if not press_html:
            press_html = "<li>No recent press coverage</li>\n"

        # Reddit — filtered to substantive categories only
        SHOW_CATS = {"NEWS", "CRITICISM", "DISCUSSION", "PRAISE"}

        reddit_week_filtered = [p for p in r.get("reddit_week", []) if p.get("category") in SHOW_CATS]
        reddit_month_filtered = [p for p in r.get("reddit_month", []) if p.get("category") in SHOW_CATS]
        total_reddit = len(reddit_week_filtered) + len(reddit_month_filtered)

        reddit_week_html = ""
        for p in reddit_week_filtered[:5]:
            title_text = _esc(_sanitize_text(p["title"][:80]))
            permalink = p.get("permalink", "")
            if permalink:
                title = f'<a href="https://www.reddit.com{_esc(permalink)}" target="_blank" class="item-link">{title_text}</a>'
            else:
                title = title_text
            score = _fmt(p["score"])
            cat = p.get("category", "OTHER")
            fg, bg = CATEGORY_COLORS.get(cat, ("#64748b", "#1e293b"))
            cat_badge = f'<span class="cat-tag" style="color:{fg};background:{bg}">{cat}</span>'
            sentiment = _analyze_sentiment(p["title"])
            s_fg, _ = _sentiment_css(sentiment)
            sent_dot = f'<span class="sentiment-dot" style="color:{s_fg}" title="{sentiment}">\u25cf</span>'
            comments_html = ""
            for c in p.get("top_comments", []):
                body = _esc(_sanitize_text(c["body"][:150]))
                comments_html += (
                    f'<li class="comment">'
                    f'<span class="comment-author">u/{_esc(c["author"])}</span> '
                    f'({_fmt(c["score"])} pts): {body}</li>\n'
                )
            comment_block = f'<ul class="comments">{comments_html}</ul>' if comments_html else ""
            reddit_week_html += f'<li>{cat_badge} {sent_dot} {title} ({score} upvotes){comment_block}</li>\n'

        reddit_month_html = ""
        for p in reddit_month_filtered[:5]:
            title_text = _esc(_sanitize_text(p["title"][:80]))
            permalink = p.get("permalink", "")
            if permalink:
                title = f'<a href="https://www.reddit.com{_esc(permalink)}" target="_blank" class="item-link">{title_text}</a>'
            else:
                title = title_text
            score = _fmt(p["score"])
            cat = p.get("category", "OTHER")
            fg, bg = CATEGORY_COLORS.get(cat, ("#64748b", "#1e293b"))
            cat_badge = f'<span class="cat-tag" style="color:{fg};background:{bg}">{cat}</span>'
            sentiment = _analyze_sentiment(p["title"])
            s_fg, _ = _sentiment_css(sentiment)
            sent_dot = f'<span class="sentiment-dot" style="color:{s_fg}" title="{sentiment}">\u25cf</span>'
            reddit_month_html += f'<li>{cat_badge} {sent_dot} {title} ({score} upvotes)</li>\n'

        trend_pct = r.get("trend_pct")
        trend_str = f"{trend_pct:+.1f}%" if trend_pct is not None else "no data"
        sub = r.get("subreddit", "")

        # Structured takeaway — sentiment-colored labels
        ts = r.get("takeaway_structured", {})
        takeaway_html = ""
        if ts.get("state"):
            state_color = {"up": "#4ade80", "down": "#f87171", "flat": "#fbbf24"}.get(r.get("trend_css", "neutral"), "#94a3b8")
            takeaway_html += f'<div class="takeaway-part"><span class="takeaway-label" style="color:{state_color}">State:</span> {_esc(_sanitize_text(ts["state"]))}</div>'
        if ts.get("context"):
            takeaway_html += f'<div class="takeaway-part"><span class="takeaway-label" style="color:#94a3b8">Context:</span> {_esc(_sanitize_text(ts["context"]))}</div>'
        if ts.get("community"):
            r_fg, _ = _sentiment_css(_analyze_sentiment(ts["community"]))
            takeaway_html += f'<div class="takeaway-part"><span class="takeaway-label" style="color:{r_fg}">Reaction:</span> {_esc(_sanitize_text(ts["community"]))}</div>'
        if ts.get("outlook"):
            o_fg, _ = _sentiment_css(_analyze_sentiment(ts["outlook"]))
            takeaway_html += f'<div class="takeaway-part"><span class="takeaway-label" style="color:{o_fg}">Outlook:</span> {_esc(_sanitize_text(ts["outlook"]))}</div>'
        if not takeaway_html:
            takeaway_html = f'<p>{_esc(_sanitize_text(r.get("takeaway", "")))}</p>'

        # Previous takeaway comparison
        prev_takeaway_html = ""
        if r.get("prev") and r["prev"].get("takeaway"):
            prev_takeaway_html = (
                f'<div class="prev-takeaway">'
                f'<strong>Previous:</strong> {_esc(r["prev"]["takeaway"])}'
                f'</div>'
            )

        # Community pulse collapsible
        community_html = ""
        if reddit_week_html or reddit_month_html:
            week_section = f'<h5>This Week</h5><ul>{reddit_week_html}</ul>' if reddit_week_html else ""
            month_section = f'<h5>This Month</h5><ul>{reddit_month_html}</ul>' if reddit_month_html else ""
            community_html = f"""
      <div class="card-community">
        <details>
          <summary>Community Pulse <span class="sub">r/{_esc(sub)}</span> — {total_reddit} substantive posts</summary>
          <div class="community-inner">
            {week_section}
            {month_section}
          </div>
        </details>
      </div>"""

        card_genre = r.get('genre', 'Other')
        card_lifecycle = _lifecycle_badge_html(r['name'])
        card_annotation = EVENT_ANNOTATIONS.get(r['name'], "")
        card_annotation_html = f'<div class="event-annotation">{_esc(card_annotation)}</div>' if card_annotation else ""
        cards_html += f"""
    <div class="card" data-genre="{card_genre}">
      <div class="card-header">
        <h3>{_esc(r['name'])}{card_lifecycle} {_genre_badge_html(card_genre)} <span class="trend-badge {r['trend_css']}">{r['trend_arrow']} {trend_str} MoM</span></h3>
        {card_annotation_html}
        <div class="card-stats">
          24h Peak: <strong>{_fmt(r['peak_24h'])}</strong> (Steam)
          {f'&nbsp;|&nbsp; Est. Total: <strong style="color:#60a5fa">{_fmt(r.get("est_total_24h", r["peak_24h"]))}</strong> ({r["steam_share"]*100:.0f}% Steam)' if not r.get('is_steam_only') else f'&nbsp;|&nbsp; Est. Total: <strong>{_fmt(r["peak_24h"])}</strong> (100% Steam)'}
          &nbsp;|&nbsp; All-Time Peak: {f'<strong style="color:#fbbf24">{_fmt(r.get("est_total_all", r["peak_all"]))}</strong> <small style="color:#556b7d">(est. all platforms)</small>' if not r.get('is_steam_only') else f'<strong>{_fmt(r["peak_all"])}</strong> <small style="color:#556b7d">(100% Steam)</small>'} ({r['pct_all']:.1f}% current)
        </div>
        {"<div class='card-trend'>" + sparkline + "</div>" if sparkline else ""}
      </div>
      <div class="card-takeaway">
        <h4>Takeaway</h4>
        {takeaway_html}
        {prev_takeaway_html}
      </div>
      <div class="card-body-2col">
        <div class="card-section">
          <h4>Developer Updates</h4>
          <ul>{news_html}</ul>
        </div>
        <div class="card-section">
          <h4>Press Coverage</h4>
          <div class="sentiment-legend">
            <span><span style="color:#4ade80">\u25cf</span> Positive</span>
            <span><span style="color:#f87171">\u25cf</span> Negative</span>
            <span><span style="color:#94a3b8">\u25cf</span> Neutral</span>
          </div>
          <ul>{press_html}</ul>
        </div>
      </div>
      {community_html}
    </div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shooter Digest - {date_str}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f1923; color: #c7d5e0;
      padding: 2rem; max-width: 1100px; margin: 0 auto;
    }}
    h1 {{ font-size: 1.8rem; margin-bottom: 0.2rem; }}
    h1 .brand-shooter {{ color: #ffffff; }}
    h1 .brand-digest {{ color: #f97316; }}
    .subtitle {{ color: #8f98a0; font-size: 0.95rem; margin-bottom: 1.5rem; }}

    /* Sticky back-nav */
    .site-nav {{
      position: sticky; top: 0; z-index: 100;
      background: rgba(15, 25, 35, 0.96);
      backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
      border-bottom: 1px solid #2a475e;
      margin: -2rem -2rem 1.5rem -2rem;
      padding: 0.65rem 2rem;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .nav-back {{
      font-size: 0.82rem; color: #8f98a0; text-decoration: none;
      transition: color 0.15s; display: flex; align-items: center; gap: 0.35rem;
    }}
    .nav-back:hover {{ color: #f97316; }}
    .nav-logo {{
      font-size: 0.9rem; font-weight: 700; color: #ffffff;
      text-decoration: none; letter-spacing: -0.3px;
    }}
    .nav-logo span {{ color: #f97316; }}

    /* Executive Summary */
    .exec-summary {{
      background: #1b2838; border-left: 3px solid #fbbf24;
      padding: 1rem 1.2rem; border-radius: 0 6px 6px 0; margin-bottom: 2rem;
    }}
    .exec-summary h2 {{ color: #fbbf24; font-size: 1rem; margin-bottom: 0.6rem; }}
    .exec-summary li {{
      margin-bottom: 0.4rem; margin-left: 1rem;
      color: #c7d5e0; font-size: 0.9rem; line-height: 1.6;
    }}
    .aggregate-chart {{
      margin-top: 1rem; padding-top: 0.8rem;
      border-top: 1px solid #2a475e;
    }}
    .aggregate-label {{
      color: #60a5fa; font-size: 0.75rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.3rem;
    }}
    .wnl-table {{
      display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.8rem;
      margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid #2a475e;
    }}
    .wnl-col {{ min-width: 0; }}
    .wnl-col table {{ width: 100%; border-collapse: collapse; }}
    .wnl-header {{
      font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.04em; padding-bottom: 0.35rem; margin-bottom: 0.3rem;
    }}

    /* Summary table */
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
    th {{
      text-align: left; padding: 0.6rem 0.7rem;
      border-bottom: 2px solid #2a475e; color: #66c0f4;
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em;
    }}
    th[data-sort] {{
      cursor: pointer; user-select: none; position: relative;
    }}
    th[data-sort]:hover {{ color: #e5e5e5; }}
    th[data-sort]::after {{
      content: '⇅'; opacity: 0.3; margin-left: 4px; font-size: 0.7rem;
    }}
    th[data-sort].asc::after {{ content: '▲'; opacity: 0.8; }}
    th[data-sort].desc::after {{ content: '▼'; opacity: 0.8; }}
    td {{ padding: 0.5rem 0.7rem; border-bottom: 1px solid #1b2838; }}
    tr:hover {{ background: #1b2838; }}
    .rank {{ color: #8f98a0; font-weight: 600; width: 40px; }}
    .game {{ font-weight: 600; color: #e5e5e5; white-space: nowrap; }}
    .num {{ font-variant-numeric: tabular-nums; text-align: right; }}
    .trend {{ text-align: center; font-weight: 600; white-space: nowrap; }}
    .trend.up {{ color: #4ade80; }}
    .trend.down {{ color: #f87171; }}
    .trend.flat {{ color: #fbbf24; }}
    .trend.neutral {{ color: #8f98a0; }}
    .pct-cell {{ width: 120px; }}
    .bar-bg {{
      background: #1b2838; border-radius: 4px; height: 6px;
      margin-bottom: 2px; overflow: hidden;
    }}
    .bar {{
      background: linear-gradient(90deg, #66c0f4, #4fa3d7);
      height: 100%; border-radius: 4px;
    }}
    .pct-cell span {{ font-size: 0.8rem; color: #8f98a0; }}
    .failed td {{ color: #555; font-style: italic; }}

    /* Key Insights */
    .insights {{
      background: #1b2838; border-left: 3px solid #66c0f4;
      padding: 1rem 1.2rem; border-radius: 0 6px 6px 0; margin-bottom: 2rem;
    }}
    .insights h2 {{ color: #66c0f4; font-size: 0.9rem; margin-bottom: 0.5rem; }}
    .insights li {{
      margin-bottom: 0.3rem; margin-left: 1rem;
      color: #b0bec5; font-size: 0.9rem; line-height: 1.5;
    }}

    /* Detail cards */
    .section-title {{
      color: #66c0f4; font-size: 1.1rem; margin: 2rem 0 1rem;
      border-bottom: 1px solid #2a475e; padding-bottom: 0.5rem;
    }}
    .card {{
      background: #1b2838; border-radius: 8px; margin-bottom: 1.2rem;
      overflow: hidden; border: 1px solid #2a475e;
    }}
    .card-header {{
      padding: 1rem 1.2rem 0.7rem; border-bottom: 1px solid #2a475e;
    }}
    .card-header h3 {{
      color: #e5e5e5; font-size: 1.1rem; margin-bottom: 0.3rem;
      display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
    }}
    .trend-badge {{
      font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 600;
    }}
    .trend-badge.up {{ background: rgba(74,222,128,0.15); color: #4ade80; }}
    .trend-badge.down {{ background: rgba(248,113,113,0.15); color: #f87171; }}
    .trend-badge.flat {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
    .trend-badge.neutral {{ background: rgba(143,152,160,0.15); color: #8f98a0; }}
    .card-stats {{ color: #8f98a0; font-size: 0.82rem; }}
    .card-stats strong {{ color: #c7d5e0; }}
    .card-trend {{ color: #8f98a0; font-size: 0.8rem; margin-top: 0.2rem; }}

    /* Takeaway — structured 4-part */
    .card-takeaway {{
      padding: 0.8rem 1.2rem; border-bottom: 1px solid #2a475e;
    }}
    .card-takeaway h4 {{
      color: #fbbf24; font-size: 0.75rem; text-transform: uppercase;
      letter-spacing: 0.04em; margin-bottom: 0.5rem;
    }}
    .card-takeaway p {{
      color: #c7d5e0; font-size: 0.85rem; line-height: 1.6; font-style: italic;
    }}
    .takeaway-part {{
      color: #c7d5e0; font-size: 0.83rem; line-height: 1.55;
      margin-bottom: 0.3rem;
    }}
    .takeaway-label {{
      color: #66c0f4; font-weight: 700; font-size: 0.72rem;
      text-transform: uppercase; letter-spacing: 0.03em;
      margin-right: 0.3rem;
    }}
    .prev-takeaway {{
      color: #8f98a0; font-size: 0.78rem; margin-top: 0.5rem;
      padding-top: 0.4rem; border-top: 1px dashed #2a475e; line-height: 1.5;
    }}

    /* Card body: 2 columns */
    .card-body-2col {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 0;
    }}
    .card-section {{ padding: 0.7rem 1rem; border-right: 1px solid #2a475e; }}
    .card-section:last-child {{ border-right: none; }}
    .card-section h4 {{
      color: #66c0f4; font-size: 0.72rem; text-transform: uppercase;
      letter-spacing: 0.04em; margin-bottom: 0.4rem;
    }}
    .card-section .sub {{ color: #8f98a0; font-size: 0.68rem; text-transform: none; }}
    .card-section ul {{ list-style: none; }}
    .card-section li {{
      color: #b0bec5; font-size: 0.8rem; line-height: 1.45;
      padding: 0.15rem 0;
    }}
    .card-section li::before {{
      content: "\\2022"; color: #66c0f4; margin-right: 0.4rem;
    }}
    .badge {{
      font-size: 0.6rem; padding: 1px 5px; border-radius: 3px;
      font-weight: 600; vertical-align: middle;
    }}
    .badge.patch {{ background: #4a3b00; color: #fbbf24; }}

    /* Genre badges */
    .genre-badge {{
      font-size: 0.55rem; padding: 2px 6px; border-radius: 3px;
      font-weight: 700; vertical-align: middle; margin-left: 0.4rem;
      letter-spacing: 0.03em; text-transform: uppercase;
      border: 1px solid rgba(255,255,255,0.08);
    }}

    /* Genre filter tabs */
    .genre-filters {{
      display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 1rem 0;
      padding: 0.6rem 0; border-bottom: 1px solid #2a475e;
    }}
    .genre-filter-btn {{
      padding: 0.35rem 0.75rem; border-radius: 6px; border: 1px solid #2a475e;
      background: #1b2838; color: #8f98a0; font-size: 0.78rem; cursor: pointer;
      font-weight: 600; transition: all 0.15s ease;
    }}
    .genre-filter-btn:hover {{ border-color: #4a90d9; color: #c6d4df; }}
    .genre-filter-btn.active {{
      background: var(--genre-active-bg, #1a3a5c);
      border-color: var(--genre-active-border, #4a90d9);
      color: var(--genre-active-color, #e5e7eb);
    }}
    .genre-filter-btn .filter-count {{
      font-size: 0.65rem; color: #556b7d; margin-left: 0.3rem;
    }}
    .genre-filter-btn.active .filter-count {{ color: #8bb9e0; }}

    /* Source tags — colors set inline per-element based on sentiment */
    .source-tag {{
      font-size: 0.6rem; padding: 1px 5px; border-radius: 3px;
      font-weight: 600; vertical-align: middle;
      background: #2d3748; color: #94a3b8;
    }}
    .sentiment-dot {{
      font-size: 0.55rem; vertical-align: middle; margin-right: 0.15rem;
    }}
    .sentiment-legend {{
      display: flex; gap: 1rem; margin-bottom: 0.5rem;
      font-size: 0.7rem; color: #8f98a0;
    }}
    .sentiment-legend span {{ display: inline-flex; align-items: center; gap: 0.2rem; }}

    /* Category tags */
    .cat-tag {{
      font-size: 0.58rem; padding: 1px 5px; border-radius: 3px;
      font-weight: 700; vertical-align: middle; margin-right: 0.3rem;
      letter-spacing: 0.03em; display: inline-block;
    }}

    /* Clickable links */
    .item-link {{
      color: #c7d5e0; text-decoration: none;
      border-bottom: 1px dotted #556b7d;
      transition: color 0.15s, border-color 0.15s;
    }}
    .item-link:hover {{
      color: #66c0f4; border-bottom-color: #66c0f4;
    }}

    /* News preview */
    .news-preview {{
      color: #8f98a0; font-size: 0.72rem; line-height: 1.35;
      margin-top: 0.15rem; max-height: 2.7em; overflow: hidden;
    }}

    /* Community pulse (collapsible) */
    .card-community {{
      padding: 0; border-top: 1px solid #2a475e;
    }}
    .card-community details {{
      padding: 0;
    }}
    .card-community summary {{
      color: #66c0f4; font-size: 0.72rem; cursor: pointer;
      text-transform: uppercase; letter-spacing: 0.04em;
      padding: 0.6rem 1rem; user-select: none;
    }}
    .card-community summary:hover {{
      background: rgba(102,192,244,0.05);
    }}
    .card-community .sub {{ color: #8f98a0; font-size: 0.68rem; text-transform: none; }}
    .community-inner {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 0;
      padding: 0 1rem 0.7rem;
    }}
    .community-inner h5 {{
      color: #8f98a0; font-size: 0.68rem; text-transform: uppercase;
      letter-spacing: 0.03em; margin-bottom: 0.3rem;
    }}
    .community-inner ul {{ list-style: none; }}
    .community-inner li {{
      color: #b0bec5; font-size: 0.78rem; line-height: 1.4;
      padding: 0.1rem 0;
    }}
    .community-inner li::before {{
      content: "\\2022"; color: #556b7d; margin-right: 0.3rem;
    }}

    /* Reddit comments */
    .comments {{
      margin-left: 0.8rem; margin-top: 0.25rem; margin-bottom: 0.3rem;
    }}
    .comments li::before {{ content: "\\21B3"; color: #556b7d; margin-right: 0.3rem; }}
    .comments li {{ font-size: 0.72rem; color: #8f98a0; line-height: 1.35; }}
    .comment-author {{ color: #66c0f4; font-size: 0.68rem; }}

    /* Sparkline chart */
    .card-trend {{ margin-top: 0.3rem; }}
    .card-trend svg {{ max-width: 240px; height: 55px; }}

    /* Release Calendar */
    .calendar-section {{ margin-top: 2rem; }}
    .cal-section {{ margin-bottom: 1rem; }}
    .cal-section-header {{
      font-size: 0.82rem; text-transform: uppercase;
      letter-spacing: 0.05em; margin-bottom: 0.4rem;
      padding: 0.4rem 0.8rem; border-radius: 0 4px 4px 0;
    }}
    .cal-section-header.past {{
      color: #8f98a0; background: #141e2b; border-left: 3px solid #556b7d;
    }}
    .cal-section-header.upcoming {{
      color: #4ade80; background: #0f2818; border-left: 3px solid #4ade80;
    }}
    .cal-section-header.future {{
      color: #fbbf24; background: #1b2838; border-left: 3px solid #fbbf24;
    }}
    .cal-count {{
      font-size: 0.65rem; color: #8f98a0; font-weight: 400;
      text-transform: none; letter-spacing: 0;
    }}
    .cal-today-divider {{
      display: flex; align-items: center; gap: 0.8rem;
      padding: 0.4rem 0; margin: 0.3rem 0;
    }}
    .cal-today-divider::before,
    .cal-today-divider::after {{
      content: ""; flex: 1; height: 1px; background: #60a5fa;
    }}
    .cal-today-divider span {{
      color: #60a5fa; font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap;
    }}
    .cal-entry {{
      display: flex; align-items: flex-start; gap: 0.6rem;
      padding: 0.4rem 0.8rem; border-bottom: 1px solid #141e2b;
    }}
    .cal-entry:hover {{ background: rgba(102,192,244,0.03); }}
    .cal-entry.estimated {{ opacity: 0.7; }}
    .cal-date {{
      min-width: 50px; color: #8f98a0; font-size: 0.75rem;
      font-weight: 600; padding-top: 0.1rem;
    }}
    .cal-game {{
      min-width: 130px; max-width: 130px; color: #e5e5e5;
      font-size: 0.8rem; font-weight: 600;
    }}
    .calendar-type {{
      font-size: 0.58rem; padding: 1px 6px; border-radius: 3px;
      font-weight: 700; min-width: 70px; text-align: center;
      display: inline-block; white-space: nowrap; flex-shrink: 0;
    }}
    .calendar-type.season {{ background: #1e3a5f; color: #3b82f6; }}
    .calendar-type.patch {{ background: #4a3b00; color: #fbbf24; }}
    .calendar-type.event {{ background: #3b1e5f; color: #a78bfa; }}
    .calendar-type.content {{ background: #1e5f2e; color: #4ade80; }}
    .calendar-type.roadmap {{ background: #1e4a5f; color: #38bdf8; }}
    .calendar-type.industry {{ background: #4a3b00; color: #f59e0b; }}
    .calendar-type.newrelease {{ background: #5f1e3a; color: #f472b6; font-weight: 800; }}
    .cal-desc {{
      color: #b0bec5; font-size: 0.78rem; line-height: 1.5; flex: 1;
      white-space: normal; word-wrap: break-word;
    }}
    .est-tag {{
      font-size: 0.55rem; color: #8f98a0; background: #1e293b;
      padding: 1px 4px; border-radius: 2px; font-weight: 600;
      vertical-align: middle; margin-left: 0.3rem;
    }}
    .cal-empty {{
      color: #556b7d; font-size: 0.78rem; font-style: italic;
      padding: 0.4rem 0.8rem;
    }}

    /* Lifecycle badge (#4) */
    .lifecycle-badge {{
      font-size: 0.55rem; padding: 1px 5px; border-radius: 3px;
      font-weight: 600; vertical-align: middle; margin-left: 0.3rem;
      text-transform: uppercase; letter-spacing: 0.03em;
    }}

    /* Sentiment dot inline in game name */
    .sent-inline {{
      font-size: 0.5rem; vertical-align: middle; margin-left: 0.25rem;
      opacity: 0.8;
    }}

    /* Inline sparkline (#6) */
    .inline-spark {{ vertical-align: middle; margin-left: 0.4rem; }}

    /* Annotation info icon — hover to see context */
    .annot-icon {{
      font-size: 0.7rem; color: #8f98a0; cursor: help;
      vertical-align: middle; margin-left: 0.2rem;
      opacity: 0.6; transition: opacity 0.15s;
    }}
    .annot-icon:hover {{ opacity: 1; color: #66c0f4; }}

    /* Genre Rollup (#9) */
    .genre-rollup {{
      margin-bottom: 2rem;
    }}
    .genre-rollup h3 {{
      color: #66c0f4; font-size: 0.9rem; margin-bottom: 0.5rem;
    }}
    .genre-rollup table {{
      width: 100%; border-collapse: collapse; font-size: 0.82rem;
    }}
    .genre-rollup th {{
      text-align: left; padding: 0.4rem 0.6rem;
      border-bottom: 2px solid #2a475e; color: #66c0f4;
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em;
    }}
    .genre-rollup td {{
      padding: 0.35rem 0.6rem; border-bottom: 1px solid #1b2838;
    }}

    /* Methodology (#7) */
    .methodology {{
      margin-top: 2rem; margin-bottom: 1rem;
    }}
    .methodology summary {{
      color: #66c0f4; font-size: 0.85rem; font-weight: 600;
      cursor: pointer; padding: 0.5rem 0;
    }}
    .methodology-content {{
      padding-top: 0.5rem;
    }}
    .methodology-disclaimer {{
      font-size: 0.78rem; color: #8f98a0; line-height: 1.5;
      margin-bottom: 1rem; padding: 0.6rem 0.8rem;
      background: rgba(27, 40, 56, 0.5); border-radius: 4px;
      border-left: 2px solid #fbbf24;
    }}
    .methodology table {{
      width: 100%; border-collapse: collapse; font-size: 0.78rem;
    }}
    .methodology th {{
      text-align: left; padding: 0.4rem 0.5rem;
      border-bottom: 2px solid #2a475e; color: #66c0f4;
      font-size: 0.68rem; text-transform: uppercase;
    }}
    .methodology td {{
      padding: 0.35rem 0.5rem; border-bottom: 1px solid #1b2838;
    }}
    .meth-note {{ font-size: 0.72rem; color: #8f98a0; }}

    /* Info tooltip (#2) */
    .info-tip {{
      display: inline-block; cursor: help; position: relative;
      font-size: 0.7rem; color: #8f98a0; margin-left: 0.2rem;
      text-decoration: none;
    }}
    .info-tip:hover {{
      color: #66c0f4;
    }}
    .info-tip:hover::after {{
      content: attr(data-tip);
      position: absolute; bottom: 120%; left: 50%;
      transform: translateX(-50%);
      background: #1b2838; color: #c7d5e0; border: 1px solid #2a475e;
      padding: 0.4rem 0.6rem; border-radius: 4px;
      font-size: 0.7rem; white-space: nowrap; z-index: 10;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }}

    .footer {{
      color: #556b7d; font-size: 0.78rem;
      border-top: 1px solid #1b2838; padding-top: 1rem; line-height: 1.6;
    }}

    @media (max-width: 800px) {{
      .card-body-2col {{ grid-template-columns: 1fr; }}
      .community-inner {{ grid-template-columns: 1fr; }}
      .card-section {{ border-right: none; border-bottom: 1px solid #2a475e; }}
      .card-section:last-child {{ border-bottom: none; }}
    }}

    /* ── Mobile-first responsive ── */
    @media (max-width: 600px) {{
      body {{ padding: 0.8rem; }}
      h1 {{ font-size: 1.4rem; }}
      .subtitle {{ font-size: 0.82rem; margin-bottom: 1rem; }}
      .site-nav {{ margin: -0.8rem -0.8rem 1.2rem -0.8rem; padding: 0.5rem 0.8rem; }}

      /* Executive Summary */
      .exec-summary {{ padding: 0.7rem 0.8rem; margin-bottom: 1.2rem; }}
      .exec-summary h2 {{ font-size: 0.9rem; margin-bottom: 0.4rem; }}
      .exec-summary li {{ font-size: 0.8rem; line-height: 1.5; margin-bottom: 0.25rem; }}

      /* WNL — compact stacked columns */
      .wnl-table {{ grid-template-columns: 1fr; gap: 0.3rem; margin-top: 0.6rem; padding-top: 0.6rem; }}
      .wnl-header {{ font-size: 0.68rem; padding-bottom: 0.2rem; margin-bottom: 0.15rem; }}
      .wnl-col table {{ margin-bottom: 0; }}
      .wnl-col table tr {{ display: flex; align-items: baseline; }}
      .wnl-col table tr:hover {{ background: none; }}
      .wnl-col table td {{
        padding: 0.15rem 0.4rem !important; font-size: 0.78rem !important;
        border-bottom: none;
      }}
      .wnl-col table td:first-child {{ flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
      .wnl-col table td:nth-child(2) {{ flex-shrink: 0; text-align: right; }}
      .wnl-col table td:nth-child(3) {{ flex-shrink: 0; min-width: 55px; text-align: right; }}

      /* Market chart */
      .aggregate-chart {{ margin-top: 0.6rem; padding-top: 0.5rem; }}
      .aggregate-label {{ font-size: 0.68rem; }}

      /* Genre filter pills — horizontal scroll */
      .genre-filters {{
        flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch;
        gap: 0.35rem; padding-bottom: 0.8rem;
        scrollbar-width: none;
      }}
      .genre-filters::-webkit-scrollbar {{ display: none; }}
      .genre-filter-btn {{
        flex-shrink: 0; font-size: 0.72rem; padding: 0.3rem 0.6rem;
      }}

      /* ── Ranking table → labeled card layout ── */
      .ranking-table thead {{ display: none; }}
      .ranking-table tbody tr {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.2rem 0.6rem;
        padding: 0.8rem 0.6rem;
        margin-bottom: 0.5rem;
        border: 1px solid #1b2838;
        border-radius: 8px;
        background: rgba(27, 40, 56, 0.4);
      }}
      .ranking-table tbody tr:hover {{ background: rgba(27, 40, 56, 0.4); }}
      .ranking-table tbody td {{
        padding: 0; border: none; text-align: left !important;
      }}
      /* Rank + Genre badge row */
      .ranking-table tbody td.rank {{
        grid-column: 1 / -1; grid-row: 1;
        font-size: 0.75rem; color: #8f98a0;
        display: flex; align-items: center; gap: 0.4rem;
      }}
      /* Game name */
      .ranking-table tbody td.game {{
        grid-column: 1 / -1; grid-row: 2;
        white-space: normal; font-size: 1.05rem; font-weight: 600;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 0.2rem;
      }}
      /* Genre badge — right side of rank row (col 3) */
      .ranking-table tbody tr > td:nth-child(3) {{
        grid-column: 1 / -1; grid-row: 1;
        display: flex; justify-content: flex-end; align-items: center;
      }}
      /* Hide sentiment dot & annotation icon on mobile cards */
      .ranking-table tbody .sent-inline {{ display: none; }}
      .ranking-table tbody .annot-icon {{ display: none; }}
      /* Stats: 2-column grid with labels */
      .ranking-table tbody td.num {{ font-size: 0.85rem; }}
      /* 24h Peak (col 4) */
      .ranking-table tbody tr > td:nth-child(4) {{
        grid-column: 1; grid-row: 3;
      }}
      .ranking-table tbody tr > td:nth-child(4)::before {{
        content: "24h Peak  "; display: block;
        font-size: 0.65rem; color: #8f98a0; font-weight: 400;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
      /* Est. Total (col 5) */
      .ranking-table tbody tr > td:nth-child(5) {{
        grid-column: 2; grid-row: 3;
      }}
      .ranking-table tbody tr > td:nth-child(5)::before {{
        content: "Est. Total  "; display: block;
        font-size: 0.65rem; color: #8f98a0; font-weight: 400;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
      /* Trend (col 6) */
      .ranking-table tbody td.trend {{
        grid-column: 1; grid-row: 4;
        text-align: left !important; font-size: 0.85rem;
        width: auto; padding-top: 0.15rem;
      }}
      .ranking-table tbody td.trend::before {{
        content: "Trend (MoM)  "; display: block;
        font-size: 0.65rem; color: #8f98a0; font-weight: 400;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
      /* All-Time Peak (col 7) */
      .ranking-table tbody tr > td:nth-child(7) {{
        grid-column: 2; grid-row: 4;
        padding-top: 0.15rem;
      }}
      .ranking-table tbody tr > td:nth-child(7)::before {{
        content: "All-Time Peak  "; display: block;
        font-size: 0.65rem; color: #8f98a0; font-weight: 400;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
      /* % of Peak (col 8) */
      .ranking-table tbody td.pct-cell {{
        grid-column: 1 / -1; grid-row: 5;
        width: auto; display: flex; align-items: center; gap: 0.4rem;
        padding-top: 0.3rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: 0.2rem;
      }}
      .ranking-table tbody td.pct-cell::before {{
        content: "% of Peak"; flex-shrink: 0;
        font-size: 0.65rem; color: #8f98a0; font-weight: 400;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
      .ranking-table .pct-cell .bar-bg {{
        width: 50px; flex-shrink: 0;
      }}
      .ranking-table .pct-cell span {{ font-size: 0.8rem; }}
      /* Genre rollup mobile */
      .genre-rollup table {{ font-size: 0.72rem; }}
      .genre-rollup th, .genre-rollup td {{ padding: 0.25rem 0.4rem; }}
      /* Methodology mobile */
      .methodology table {{ font-size: 0.7rem; }}
      .methodology th, .methodology td {{ padding: 0.25rem 0.3rem; }}
      .meth-note {{ font-size: 0.6rem; }}
      /* Failed rows */
      .ranking-table tbody tr.failed {{
        display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.5rem 0.6rem;
      }}

      /* Section title */
      .section-title {{ font-size: 1.1rem; }}

      /* Detail cards */
      .card {{ margin-bottom: 1rem; }}
      .card-header {{ padding: 0.6rem 0.8rem; }}
      .card-header-left h3 {{ font-size: 0.95rem; }}
      .card-section {{ padding: 0.6rem 0.8rem; }}

      /* Calendar */
      .cal-entry {{
        flex-wrap: wrap; gap: 0.3rem; padding: 0.4rem 0.5rem;
      }}
      .cal-game {{ min-width: 0; max-width: none; font-size: 0.75rem; }}
      .cal-desc {{ font-size: 0.72rem; width: 100%; }}

      /* Footer */
      .footer {{ font-size: 0.7rem; }}

      /* Insights */
      .insights li {{ font-size: 0.82rem; }}

      /* Generic table overflow — catches any table not already styled responsively */
      .genre-rollup table {{ display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; white-space: nowrap; }}
      .genre-rollup th, .genre-rollup td {{ font-size: 0.78rem; padding: 0.3rem 0.5rem; }}
    }}
  </style>
</head>
<body>
  <nav class="site-nav">
    <a href="index.html" class="nav-back">&#8592; All Digests</a>
    <a href="index.html" class="nav-logo">Shooter<span>Digest</span></a>
  </nav>
  <h1><span class="brand-shooter">Shooter</span><span class="brand-digest">Digest</span></h1>
  <p class="subtitle">Week of {date_str} &mdash; Player Data, Updates &amp; Community Intel</p>

{exec_html}

{genre_tabs_html}

  <table class="ranking-table">
    <thead>
      <tr>
        <th data-sort="num" data-col="0">Rank</th>
        <th data-sort="str" data-col="1">Game</th>
        <th data-sort="str" data-col="2">Genre</th>
        <th data-sort="num" data-col="3" style="text-align:right">24h Peak<br><small>(Steam)</small></th>
        <th data-sort="num" data-col="4" style="text-align:right">Est. Total<br><small>(All Plat.)</small> <a href="#methodology" class="info-tip" data-tip="Steam 24h peak &divide; Steam share. Click for methodology.">\u24d8</a></th>
        <th data-sort="num" data-col="5">Trend<br><small>(MoM)</small></th>
        <th data-sort="num" data-col="6" style="text-align:right">All-Time Peak<br><small>(Est. All Plat.)</small></th>
        <th data-sort="num" data-col="7">% of Peak</th>
      </tr>
    </thead>
    <tbody>
{table_rows}    </tbody>
  </table>

{genre_rollup_html}

{_build_insights_html(results)}

  <h2 class="section-title">Game Details</h2>
{cards_html}

{_render_calendar_html(_build_release_calendar(results))}

{methodology_html}

  <div class="footer">
    Generated: {timestamp}<br>
    Data: SteamCharts, Steam News API, Reddit, Google News<br>
    <small>
      <strong>Color key:</strong>
      White = raw Steam data &nbsp;|&nbsp;
      <span style="color:#60a5fa">Blue</span> = estimated total across all platforms (current) &nbsp;|&nbsp;
      <span style="color:#fbbf24">Gold</span> = estimated total across all platforms (all-time)<br>
      Est. Total = Steam peak &divide; Steam share. Trend = month-over-month from SteamCharts.<br>
      Platform splits from EA, Krafton, NetEase earnings, Alinea Analytics, and community trackers. Extrapolated where official data unavailable.
    </small>
  </div>

  <script>
  // Genre filter tabs
  document.querySelectorAll('.genre-filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      // Update active state
      document.querySelectorAll('.genre-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const genre = btn.dataset.genre;

      // Filter table rows
      document.querySelectorAll('table tbody tr[data-genre]').forEach(row => {{
        row.style.display = (genre === 'All' || row.dataset.genre === genre) ? '' : 'none';
      }});

      // Filter cards
      document.querySelectorAll('.card[data-genre]').forEach(card => {{
        card.style.display = (genre === 'All' || card.dataset.genre === genre) ? '' : 'none';
      }});
    }});
  }});

  // Sortable table columns
  document.querySelectorAll('th[data-sort]').forEach(th => {{
    th.addEventListener('click', () => {{
      const table = th.closest('table');
      const tbody = table.querySelector('tbody');
      const col = parseInt(th.dataset.col);
      const type = th.dataset.sort;
      const isAsc = th.classList.contains('asc');
      const dir = isAsc ? -1 : 1;

      // Update header classes
      table.querySelectorAll('th[data-sort]').forEach(h => h.classList.remove('asc', 'desc'));
      th.classList.add(isAsc ? 'desc' : 'asc');

      // Get sortable rows (skip failed rows)
      const rows = Array.from(tbody.querySelectorAll('tr[data-genre]'));

      rows.sort((a, b) => {{
        const cellA = a.children[col];
        const cellB = b.children[col];

        if (type === 'num') {{
          const vA = parseFloat(cellA.dataset.value || '0');
          const vB = parseFloat(cellB.dataset.value || '0');
          return (vA - vB) * dir;
        }} else {{
          const vA = cellA.textContent.trim().toLowerCase();
          const vB = cellB.textContent.trim().toLowerCase();
          return vA.localeCompare(vB) * dir;
        }}
      }});

      rows.forEach(row => tbody.appendChild(row));
    }});
  }});
  </script>
</body>
</html>
"""


def _build_insights_html(results: list[dict]) -> str:
    if not results:
        return ""
    items = []

    if len(results) >= 3:
        top3 = ", ".join(r["name"] for r in results[:3])
        items.append(f"<strong>Biggest populations:</strong> {top3}")

    with_trend = [r for r in results if r.get("trend_pct") is not None]
    if with_trend:
        gainer = max(with_trend, key=lambda r: r["trend_pct"])
        if gainer["trend_pct"] > 0:
            items.append(
                f'<strong>Biggest gainer:</strong> {gainer["name"]} '
                f'({gainer["trend_pct"]:+.1f}%)'
            )
        loser = min(with_trend, key=lambda r: r["trend_pct"])
        if loser["trend_pct"] < 0:
            items.append(
                f'<strong>Biggest decline:</strong> {loser["name"]} '
                f'({loser["trend_pct"]:+.1f}%)'
            )

    closest = max(results, key=lambda r: r.get("pct_all", 0))
    items.append(
        f'<strong>Closest to all-time peak:</strong> {closest["name"]} '
        f'({closest["pct_all"]:.1f}%)'
    )

    li = "\n".join(f"      <li>{i}</li>" for i in items)
    return f"""  <div class="insights">
    <h2>Key Insights</h2>
    <ul>
{li}
    </ul>
  </div>"""


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(results: list[dict], failed_names: list[str],
                      overall_takeaways: list[str]) -> str:
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    timestamp = today.strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"# Shooter Digest - Week of {date_str}",
        "",
        "## Executive Summary",
        "",
    ]
    for t in overall_takeaways:
        lines.append(f"- {_sanitize_text(t)}")
    lines += ["", "---", ""]

    # Winners / Neutrals / Losers
    wnl = _generate_winners_neutrals_losers(results)
    lines.append("### Winners (Growing >2% MoM)")
    lines.append("")
    if wnl["winners"]:
        lines.append("| Game | Trend | 24h Peak (Steam) |")
        lines.append("|------|-------|-------------------|")
        for g in wnl["winners"]:
            t = f'{g["trend_pct"]:+.1f}%' if g["trend_pct"] is not None else "—"
            lines.append(f'| {g["name"]} | {g["trend_arrow"]} {t} | {_fmt(g["peak_24h"])} |')
    else:
        lines.append("*None*")
    lines.append("")

    lines.append("### Holding Steady (-2% to +2% MoM)")
    lines.append("")
    if wnl["neutrals"]:
        lines.append("| Game | Trend | 24h Peak (Steam) |")
        lines.append("|------|-------|-------------------|")
        for g in wnl["neutrals"]:
            t = f'{g["trend_pct"]:+.1f}%' if g["trend_pct"] is not None else "—"
            lines.append(f'| {g["name"]} | {g["trend_arrow"]} {t} | {_fmt(g["peak_24h"])} |')
    else:
        lines.append("*None*")
    lines.append("")

    lines.append("### Losers (Declining >2% MoM)")
    lines.append("")
    if wnl["losers"]:
        lines.append("| Game | Trend | 24h Peak (Steam) |")
        lines.append("|------|-------|-------------------|")
        for g in wnl["losers"]:
            t = f'{g["trend_pct"]:+.1f}%' if g["trend_pct"] is not None else "—"
            lines.append(f'| {g["name"]} | {g["trend_arrow"]} {t} | {_fmt(g["peak_24h"])} |')
    else:
        lines.append("*None*")
    lines.append("")

    lines += ["---", ""]

    # Simplified table
    lines.append("## Player Count Leaderboard")
    lines.append("")
    lines.append("| Rank | Game | Genre | 24h Peak (Steam) | Est. Total (All) | Trend (MoM) | All-Time (Est.) | % of Peak |")
    lines.append("|------|------|-------|-------------------|-------------------|-------------|-----------------|-----------|")

    for r in results:
        trend_pct = r.get("trend_pct")
        trend_str = f"{trend_pct:+.1f}%" if trend_pct is not None else "?"
        est_total = _fmt(r.get('est_total_24h', r['peak_24h']))
        est_all_time = _fmt(r.get('est_total_all', r['peak_all']))
        platform_note = " (100% Steam)" if r.get('is_steam_only') else f" ({r['steam_share']*100:.0f}% Steam)"
        all_time_note = " (100% Steam)" if r.get('is_steam_only') else f" ({r['steam_share']*100:.0f}% Steam)"
        genre_short = GENRE_SHORT.get(r.get('genre', 'Other'), r.get('genre', 'Other'))
        lines.append(
            f"| {r['rank']} "
            f"| {r['name']} "
            f"| {genre_short} "
            f"| {_fmt(r['peak_24h'])} "
            f"| {est_total}{platform_note} "
            f"| {r['trend_arrow']} {trend_str} "
            f"| {est_all_time}{all_time_note} "
            f"| {r['pct_all']:.1f}% |"
        )

    for name in failed_names:
        lines.append(f"| - | {name} | - | - | - | - | - | - |")

    lines += ["", "---", ""]

    # Detail sections
    for r in results:
        trend_pct = r.get("trend_pct")
        trend_str = f"{trend_pct:+.1f}%" if trend_pct is not None else "no data"
        md_genre = r.get('genre', 'Other')
        lines.append(f"### {r['name']} [{md_genre}] ({r['trend_arrow']} {trend_str})")
        lines.append("")
        # Platform context
        if not r.get('is_steam_only'):
            lines.append(
                f"*Platform: {r['steam_share']*100:.0f}% Steam — "
                f"24h Peak {_fmt(r['peak_24h'])} (Steam) / "
                f"~{_fmt(r.get('est_total_24h', r['peak_24h']))} (Est. All Platforms)*"
            )
        else:
            lines.append(
                f"*Platform: 100% Steam — "
                f"24h Peak {_fmt(r['peak_24h'])} / "
                f"All-Time Peak {_fmt(r['peak_all'])}*"
            )
        lines.append("")

        # Structured takeaway — with sentiment markers
        ts = r.get("takeaway_structured", {})
        if ts:
            if ts.get("state"):
                state_mark = {"up": "+", "down": "-", "flat": "~"}.get(r.get("trend_css", "neutral"), "~")
                lines.append(f"**State [{state_mark}]:** {_sanitize_text(ts['state'])}")
            if ts.get("context"):
                lines.append(f"**Context [~]:** {_sanitize_text(ts['context'])}")
            if ts.get("community"):
                r_s = _analyze_sentiment(ts["community"])
                r_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(r_s, "~")
                lines.append(f"**Reaction [{r_mark}]:** {_sanitize_text(ts['community'])}")
            if ts.get("outlook"):
                o_s = _analyze_sentiment(ts["outlook"])
                o_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(o_s, "~")
                lines.append(f"**Outlook [{o_mark}]:** {_sanitize_text(ts['outlook'])}")
        else:
            lines.append(f"**Takeaway:** {_sanitize_text(r.get('takeaway', ''))}")
        if r.get("prev") and r["prev"].get("takeaway"):
            lines.append("")
            lines.append(f"*Previous: {r['prev']['takeaway']}*")
        lines.append("")

        # Trend line with month labels
        if r["avg_trend"]:
            trend_parts = []
            for m in r["avg_trend"]:
                month_label = m.get("month", "")
                if month_label == "Last 30 Days":
                    month_label = datetime.now().strftime("%b") + " (30d)"
                else:
                    try:
                        dt = datetime.strptime(month_label, "%B %Y")
                        month_label = dt.strftime("%b %Y")
                    except ValueError:
                        pass
                trend_parts.append(f"{month_label}: {_fmt_k(m['avg'])}")
            arrow = ' \u2192 '
            lines.append(f"**Trend:** {arrow.join(trend_parts)} avg players")
            lines.append("")

        # Developer updates — with sentiment markers
        if r.get("news"):
            lines.append("**Developer Updates:**")
            for n in r["news"][:3]:
                patch = " [PATCH]" if n["is_patch"] else ""
                title = _sanitize_text(n["title"][:80])
                sentiment = _analyze_sentiment(n.get("title", "") + " " + (n.get("contents", "") or "")[:200])
                s_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(sentiment, "~")
                lines.append(f'- [{s_mark}] {title} \u2014 {n["date"]}{patch}')
                summary = _extract_news_summary(n)
                if summary:
                    lines.append(f'  > {_sanitize_text(summary)}')
            lines.append("")

        # Press coverage — with sentiment markers
        ext_news = r.get("external_news", [])
        if ext_news:
            lines.append("**Press Coverage:**")
            for a in ext_news[:4]:
                title = _sanitize_text(a["title"][:75])
                source = f" ({a['source']})" if a.get("source") else ""
                date = f" {a['date']}" if a.get("date") else ""
                sentiment = _analyze_sentiment(a.get("title", ""))
                s_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(sentiment, "~")
                lines.append(f'- [{s_mark}] {title}{source}{date}')
            lines.append("")

        # Reddit — with sentiment markers
        SHOW_CATS = {"NEWS", "CRITICISM", "DISCUSSION", "PRAISE"}
        sub = r.get("subreddit", "")

        weekly = [p for p in r.get("reddit_week", []) if p.get("category") in SHOW_CATS]
        if weekly:
            lines.append(f"**Community Pulse — This Week** (r/{sub}):")
            for p in weekly[:5]:
                cat = p.get("category", "OTHER")
                title = _sanitize_text(p["title"][:80])
                sentiment = _analyze_sentiment(p["title"])
                s_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(sentiment, "~")
                lines.append(f'- [{cat}] [{s_mark}] {title} ({_fmt(p["score"])} upvotes)')
                for c in p.get("top_comments", []):
                    body = _sanitize_text(c["body"][:120].replace("\n", " "))
                    lines.append(f'  > u/{c["author"]} ({_fmt(c["score"])} pts): {body}')
            lines.append("")

        monthly = [p for p in r.get("reddit_month", []) if p.get("category") in SHOW_CATS]
        if monthly:
            lines.append(f"**Community Pulse — This Month** (r/{sub}):")
            for p in monthly[:5]:
                cat = p.get("category", "OTHER")
                title = _sanitize_text(p["title"][:80])
                sentiment = _analyze_sentiment(p["title"])
                s_mark = {"positive": "+", "negative": "-", "neutral": "~"}.get(sentiment, "~")
                lines.append(f'- [{cat}] [{s_mark}] {title} ({_fmt(p["score"])} upvotes)')
            lines.append("")

    # Release & Patch Calendar (curated, forward-looking)
    cal_data = _build_release_calendar(results)
    lines += ["---", ""]
    lines.append("## Release & Patch Calendar")
    lines.append("")

    def _md_cal_table(entries, section_label):
        md = [f"### {section_label}", ""]
        if not entries:
            md.append(f"*No events tracked.*")
            md.append("")
            return md
        md.append("| Date | Game | Type | Details |")
        md.append("|------|------|------|---------|")
        for e in entries:
            desc = _sanitize_text(e.get("desc", ""))
            url = e.get("url", "")
            if url:
                desc = f"[{desc}]({url})"
            est = " *(estimated)*" if e.get("estimated") else ""
            md.append(f"| {e.get('date_str', '')} | {e['game']} | {e['type']} | {desc}{est} |")
        md.append("")
        return md

    lines += _md_cal_table(cal_data.get("this_week", []), "This Week")
    lines.append(f"*— TODAY ({datetime.now().strftime('%b %d')}) —*")
    lines.append("")
    lines += _md_cal_table(cal_data.get("coming_up", []), "Coming Up (Next 2 Weeks)")

    for month_name, entries in cal_data.get("months", {}).items():
        lines += _md_cal_table(entries, month_name)

    lines += ["---", ""]
    lines.append(f"*Generated: {timestamp}*  ")
    lines.append("*Data: SteamCharts, Steam News API, Reddit, Google News*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("  Shooter Digest - Fetching player data + context...")
    print("  (This takes about 3-4 minutes for 15 titles)")
    print()

    results = scrape_all()

    scraped_names = {r["name"] for r in results}
    failed_names = [g["name"] for g in GAMES if g["name"] not in scraped_names]

    success = len(results)
    total = len(GAMES)
    print()
    print(f"  Done! Got data for {success}/{total} games.")

    if total - success > 5:
        print("  WARNING: Many games failed - there may be a connection issue.")

    # Enrich
    results = _enrich(results)

    # History comparison
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)

    previous = _load_previous_history(out_dir)
    _compute_deltas(results, previous)
    if previous:
        print(f"  Loaded previous data for comparison ({len(previous)} games)")
    else:
        print("  No previous history found (first run)")

    # Generate takeaways
    for r in results:
        _generate_game_takeaway(r)
    overall_takeaways = _generate_overall_takeaways(results)
    print(f"  Generated takeaways for {len(results)} games + overall")

    # Save outputs
    date_str = datetime.now().strftime("%Y-%m-%d")

    md_path = os.path.join(out_dir, f"digest_{date_str}.md")
    with open(md_path, "w") as f:
        f.write(generate_markdown(results, failed_names, overall_takeaways))

    html_path = os.path.join(out_dir, f"digest_{date_str}.html")
    with open(html_path, "w") as f:
        f.write(generate_html(results, failed_names, overall_takeaways))

    # Save history
    _save_history(results, out_dir)

    print(f"  Saved to: {out_dir}/")
    print()
    print(f"  Open this in your browser:")
    print(f"  {html_path}")
    print()


if __name__ == "__main__":
    main()
