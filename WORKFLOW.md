# ShooterDigest — Agent Workflow

This file defines agent behavior for automated digest runs. Inspired by the Symphony WORKFLOW.md
pattern: agent policy lives in the repo, versioned with the code.

---

## What this workflow does

Every Monday at 7am ET, a GitHub Actions job runs the weekly digest pipeline:

1. `ingest.py` — scrapes Steam, Reddit, Google News for all tracked games and stores a snapshot
2. `render_from_store.py` — renders the snapshot into HTML and writes it to Postgres
3. Railway auto-deploys on push (for digest commits) or reads from Postgres directly

The agent's job is to get the digest to **Human Review** state — a live page at
`shooter.pyon.dev` with fresh data. It does not decide what's "done."

---

## Handoff states

| State | Meaning |
|---|---|
| 🟡 Running | Pipeline in progress |
| 🟢 Human Review | Digest is live, data looks reasonable — Michael reviews |
| 🔴 Failed | Pipeline errored; agent should diagnose and fix before next Monday |
| ⚪ Skipped | No new data available (Steam Charts blocked, Reddit 403s) — known, non-blocking |

**The agent stops at Human Review. Michael decides if the digest is publishable.**

---

## Agent behavior rules

### Data ingestion
- Steam concurrent player data is the authoritative signal. If Steam scrape fails, the digest
  is incomplete — flag it, do not silently serve stale data.
- Reddit 403s from GitHub Actions IPs are **expected and non-blocking**. The digest runs on
  Steam + news data when Reddit is unavailable.
- If all sources fail for a game, include the game with a "data unavailable" marker rather than
  dropping it silently.

### Error handling
- `SyntaxError` or `TypeError` in Python: fix the root cause, do not patch around it.
- `datetime not JSON serializable`: use `_DatetimeEncoder` in `pipeline_store.py` (already done).
- f-string nested quote errors: use single quotes inside double-quoted f-strings (Python 3.11).
- After any fix: run `python3 -c "import ast; ast.parse(open('main.py').read())"` before pushing.

### Stall detection
- If the ingest step runs longer than 10 minutes with no output, something is stuck.
- Common cause: a scraper is hanging on a blocked URL. Check logs for the last printed game name.
- Fix: add a per-request timeout (default 10s) to the hanging scraper call.

### What NOT to do
- Do not skip games to make the digest "pass." Missing data is worse than a failed run.
- Do not change tracked game list without updating `CLAUDE.md`.
- Do not commit generated HTML to the repo (it belongs in Postgres now).
- Do not push fixes to CI to test them. Run `python3 -c "import ast; ast.parse(...)"` locally first.

---

## Tracked games (source of truth: `main.py`)

CS2, Valorant, Apex Legends, PUBG, Rainbow Six Siege, Overwatch 2, Marvel Rivals,
Call of Duty (Warzone/BO6), Halo Infinite, Delta Force, Arc Raiders, Battlefield 6

---

## Pipeline architecture

```
ingest.py
  └── collect_pipeline_snapshot()   ← main.py
        ├── Steam Charts (concurrent players, history)
        ├── Steam News API (patch notes, updates)
        ├── Reddit (weekly + monthly top posts, top comments)
        └── Google News RSS (recent coverage)
  └── save_snapshot()               ← pipeline_store.py (SQLite locally, Postgres on Railway)

render_from_store.py
  └── load_snapshot()               ← pipeline_store.py
  └── render HTML                   ← main.py
  └── write to Postgres             ← db.py

server.py
  └── serves latest digest from Postgres at /
```

---

## Environment variables (Railway)

| Var | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection string (Railway auto-injects) |
| `REDDIT_CLIENT_ID` | No | If absent, Reddit scrape is skipped gracefully |
| `REDDIT_CLIENT_SECRET` | No | See above |

---

## Known issues / recurring patterns

- **Python 3.11 f-string nested quotes**: GitHub Actions uses 3.11. Use `r['name']` not `r["name"]`
  inside double-quoted f-strings. Python 3.12+ allows this; 3.11 does not.
- **Reddit 403 on GitHub Actions**: Reddit blocks datacenter IPs. This is permanent and expected.
  The digest degrades gracefully without Reddit data.
- **SteamCharts Cloudflare blocks**: Occasional. The backfill system handles this. Do not remove
  the backfill path.
- **`datetime` not JSON serializable**: Fixed via `_DatetimeEncoder` in `pipeline_store.py`.
  If this resurfaces, check any new dict keys added to the snapshot that might carry datetime values.

---

## Maintenance checklist (before each Monday run)

- [ ] GitHub Actions has "Read and write permissions" enabled (Settings → Actions → General)
- [ ] `DATABASE_URL` is set in Railway environment
- [ ] No Python syntax errors: `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['main.py','ingest.py','pipeline_store.py']]"`

---

_Last updated: 2026-03-16. Update this file when pipeline architecture changes._
