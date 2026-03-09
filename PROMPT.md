# ShooterDigest — Autoresearch Prompt

**Pattern:** Human defines the objective here. Agent iterates on `scraper.py` and `main.py`.
**Loop:** Run → measure coverage score → commit if better → repeat.
**Branch:** Always work on a `research/<description>` branch. Never push directly to `main`.

---

## Objective

Maximize data coverage and accuracy for the weekly ShooterDigest report.

A "good" digest has:
- Steam peak concurrents for all tracked games (not fallback/zero values)
- Complete monthly history (≥6 months) for all games — this drives trend calculations
- Derived fields (trend_pct, trend_arrow, pct_all, avg_trend, peak windows) computed correctly after any backfill
- No stale derived values — if backfill runs, re-enrich always runs after

A "bad" digest has:
- Games with `peak_24h = 0` or `peak_all = 0` (scraper failed, no fallback)
- Games with `months = []` or `months` with < 3 entries (trend math breaks)
- Derived fields that disagree with the raw monthly data
- Cloudflare blocks that silently produce zero-data instead of triggering fallback

---

## Success Metric (Your "Validation Loss")

After running `python main.py`, compute a **coverage score**:

```python
# Run this after each iteration to measure improvement
import json, re
from pathlib import Path

# Parse the most recent digest HTML for data quality signals
digest = sorted(Path("output").glob("digest_*.html"))[-1].read_text()

# Count games with valid peak data (non-zero)
valid_peak = len(re.findall(r'"peak_24h":\s*[1-9]', digest))
total_games = len(re.findall(r'"name":', digest))

# Count games with ≥6 months of history
rich_history = len(re.findall(r'"months":\s*\[[^\]]{100,}', digest))

score = (valid_peak / max(total_games, 1)) * 0.6 + (rich_history / max(total_games, 1)) * 0.4
print(f"Coverage score: {score:.3f} ({valid_peak}/{total_games} valid peaks, {rich_history}/{total_games} rich history)")
```

**Target: score ≥ 0.90.** Commit only when score improves over the previous run.

---

## Context (Read Before Iterating)

### Architecture
- `scraper.py` — all data collection (Steam Charts, Steam API, Reddit, Google News RSS)
- `main.py` — orchestration: calls scraper → `_enrich()` → backfill → renders HTML
- `_enrich()` runs at line ~1066 in `main.py` — computes all derived fields
- Backfill runs after `_enrich()` at line ~4300 — replaces missing peak/month data from history files
- **Critical order:** Enrich → Backfill → Re-enrich. Currently, re-enrich does NOT run after backfill. This is a known bug.

### Current Blockers
1. **SteamCharts Cloudflare block (active since early March 2026)**
   - `cloudscraper` is the current workaround in `scraper.py`
   - It sometimes still fails silently (returns a Cloudflare challenge page instead of data)
   - The `_steamcharts_get()` function validates for this but may need improvement
   - Fallback path: use Steam API directly for peak concurrents when SteamCharts fails

2. **Derived fields go stale after backfill**
   - `trend_pct`, `trend_arrow`, `pct_all`, `avg_trend`, and peak windows are computed in `_enrich()`
   - Backfill replaces raw `months` and `peak_all` data but doesn't re-run `_enrich()`
   - Fix: call `_enrich()` on the backfilled results before rendering

3. **History file quality check missing**
   - `main.py` loads the "most recent" history file but doesn't validate data quality
   - A partial scrape (e.g., Cloudflare blocked mid-run) can produce a "recent" file with zero data
   - Fix: select the most recent file where ≥80% of games have non-zero peak_24h

---

## What to Iterate On

Agent: iterate on these files only. Do not touch HTML rendering, CSS, or server.py.

**Primary targets:**
- `scraper.py` — improve data collection reliability
- `main.py` (lines 1066–1200, 4280–4370) — fix enrich/backfill ordering, history selection

**Iteration ideas (ordered by expected impact):**
1. Add re-enrich step after backfill (single function call, high-confidence fix)
2. Improve history file selection (quality-based, not recency-based)
3. Improve Cloudflare detection in `_steamcharts_get()` — check for challenge indicators in response body
4. Add Steam API fallback for peak concurrents when SteamCharts is unavailable
5. Add retry with exponential backoff specifically for Cloudflare-blocked responses
6. Add per-game coverage logging so it's easy to see which games are failing and why

**Do not:**
- Change the `GAMES` list or `steam_share` values
- Modify HTML output structure (dashboard rendering is separate)
- Add new data sources without first getting all existing sources to ≥0.90 coverage

---

## Iteration Loop

```bash
# 1. Make your change to scraper.py or main.py
# 2. Run the digest
python main.py

# 3. Score the output
python -c "
import json, re
from pathlib import Path
digest = sorted(Path('output').glob('digest_*.html'))[-1].read_text()
valid_peak = len(re.findall(r'\"peak_24h\":\s*[1-9]', digest))
total_games = len(re.findall(r'\"name\":', digest))
rich_history = len(re.findall(r'\"months\":\s*\[[^\]]{100,}', digest))
score = (valid_peak / max(total_games, 1)) * 0.6 + (rich_history / max(total_games, 1)) * 0.4
print(f'Score: {score:.3f} | Peaks: {valid_peak}/{total_games} | Rich history: {rich_history}/{total_games}')
"

# 4. If score improved: git commit with the score in the message
# 5. If score regressed: revert and try a different approach
```

---

## Commit Format

```
[score: 0.87 → 0.92] fix re-enrich after backfill

What changed: called _enrich() on backfilled results before HTML render.
Why it helped: trend_pct/trend_arrow were stale for 4 backfilled games.
Next to try: history file quality-based selection.
```

Each commit message should include:
- Score delta (before → after)
- One-line description of the change
- Why it helped
- What to try next

---

## Done When

Score ≥ 0.90 across 3 consecutive runs (not just one lucky run).
Open a PR to `main` with a summary of all commits and final score.
