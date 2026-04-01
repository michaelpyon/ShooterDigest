# CHANGES

Audit date: 2026-03-27

Scope:
- Read the repo code and project config.
- Reviewed the scrape pipeline, render templates, security posture, config drift, and GitHub Actions.
- Made a small set of high-confidence fixes.
- Did not commit, delete files, or touch pre-existing generated artifacts beyond code/config changes.

## Fixes Applied

1. Retry policy is now transient-only, and SteamCharts requests now retry too.
   - Files: `scraper.py:19-83`
   - Before: all `RequestException`s were retried, including permanent 403/404 responses, while the SteamCharts path had no retry wrapper at all.
   - After: retries only happen for timeouts, connection failures, and retryable HTTP statuses (`408`, `429`, `5xx`), and both regular HTTP and SteamCharts requests share the same retry budget.

2. Failed source fetches are now recorded in `fetch_runs`.
   - Files: `source_cache.py:73-81`
   - Before: only cache hits and successful fetches were logged; failed attempts disappeared from the observability trail.
   - After: request failures record a status code when available before re-raising.

3. The HTTP server no longer exposes arbitrary repo files.
   - Files: `server.py:14-16`, `server.py:210-279`
   - Before: unknown routes fell through to `SimpleHTTPRequestHandler`, which could serve repo-root files that were copied into the image.
   - After: the server is effectively allowlist-only for digest routes and the explicit static assets it needs.

4. Docker build context now excludes `.env*`, `docs/`, and `output/`.
   - Files: `.dockerignore:1-10`
   - Reason: defense in depth. Even with the server fix, shipping local env files or generated output in the runtime image is unnecessary risk and bloat.

5. Site and social metadata are now config-driven instead of hardcoded in multiple places.
   - Files: `main.py:21-23`, `server.py:14-16`, `.env.example:7-10`
   - Added: `SITE_URL`, `TWITTER_SITE_HANDLE`, `TWITTER_CREATOR_HANDLE`
   - Result: OG/Twitter tags and share links can be changed without editing code.

6. Historical re-renders now respect the snapshot date and stored generation time.
   - Files: `main.py:2881-2894`, `main.py:5194-5209`, `main.py:5401-5435`, `main.py:5766-5816`
   - Before: rendering an older stored snapshot stamped the current date/time into the masthead, footer, markdown, and calendar-relative sections.
   - After: render output uses the snapshot's `date` and `generated_at`.

7. Archive teaser parsing now supports both the old and current executive-summary phrasing.
   - Files: `main.py:5457-5477`
   - Before: newer digests like `2026-03-09` only showed `15 games` / `16 games` in `index.html` because the regex still expected the old `at +X% month-over-month` wording.
   - After: both old and new phrasing parse correctly.
   - Note: I did not overwrite the already-dirty checked-in `docs/index.html`; the fix will apply on the next render.

8. CI now checks the Python versions that matter.
   - Files: `.github/workflows/ci.yml:8-22`
   - Before: CI only compiled on Python `3.12`, while the scheduled digest workflow runs on `3.11`.
   - After: CI runs on both `3.11` and `3.12`, and compiles only the source files instead of traversing the whole repo.

## Findings Not Fixed

1. Full source failure still drops a game out of the detailed digest instead of rendering a true `data unavailable` state.
   - Files: `main.py:1294-1298`, `WORKFLOW.md:41-42`
   - Current behavior: if both SteamCharts and the Steam API fail, `scrape_games()` `continue`s and the title only shows up later as a failed summary row.
   - Risk: this conflicts with the workflow policy and weakens week-to-week continuity in the detailed report.

2. Rate limiting is crude, hardcoded, and applied even on cache hits.
   - Files: `main.py:17`, `main.py:1276-1353`
   - Current behavior: fixed `time.sleep(1)` calls are sprinkled between source requests, plus a global `DELAY_BETWEEN_REQUESTS = 2`.
   - Risk: unnecessary runtime on cached runs, awkward tuning, and no per-source control.
   - Recommendation: move this to config and gate sleeps on real network fetches instead of every call.

3. Snapshot comparison/backfill still depends on local `output/history`, not the pipeline store.
   - Files: `main.py:5627-5688`
   - Current behavior: delta/backfill logic reads the most recent local history JSON.
   - Risk: CI and Railway can be stale or empty depending on what is checked into the repo/workspace, even though Postgres already stores the canonical snapshots.
   - Recommendation: load the prior snapshot from `pipeline_store` first and only fall back to local history if needed.

4. SteamSpy discovery has no retry/caching layer and keeps its own hardcoded pacing.
   - Files: `discovery.py:24-40`, `discovery.py:59-70`
   - Current behavior: plain `requests.get(...)`, one try, fixed `TAG_REQUEST_SLEEP = 2`.
   - Risk: discovery is more brittle than the main scrape path and uses a separate policy surface.

5. Project docs are out of sync with the implementation.
   - Files: `README.md:5-16`, `README.md:35-60`, `WORKFLOW.md:10-17`, `WORKFLOW.md:63-98`
   - Examples:
     - `README.md` lists 10 tracked games, but the code tracks more than that.
     - `README.md` still documents `output/pipeline/YYYY-MM-DD.json` as the stored pipeline output path, while snapshot storage now routes through Postgres plus optional local export.
     - `WORKFLOW.md` still references an outdated tracked-games list and optional Reddit secrets that are not consumed by the current scraper.

6. The weekly workflow's cron comment is DST-inaccurate.
   - Files: `.github/workflows/weekly-digest.yml:5-6`
   - Current behavior: comment says `0 12 * * 1` is `7am ET / 4am PT`.
   - Reality: UTC cron does not track US daylight saving time; the local runtime shifts during the year.

7. Several editorial/config datasets still live inline in Python and should probably move to data/config files if this project keeps growing.
   - Examples:
     - `DELAY_BETWEEN_REQUESTS` in `main.py:17`
     - platform multiplier notes and lifecycle annotations in `main.py`
     - industry release calendar in `main.py:1996-2051`
   - Risk: code deploys become the only way to update operational copy/data that is not actually executable logic.

## Security Notes

1. SQL usage looks safe in the current codebase.
   - `db.py` uses parameterized queries throughout.

2. I did not find hardcoded API keys or secrets in tracked source files.
   - `DATABASE_URL` and the newsletter email are environment-driven.

3. The biggest concrete security issue in the audited code was repo-root static file exposure from `server.py`.
   - That is fixed.

## Template / Newsletter Quality Notes

1. The main HTML template is structurally strong and unusually detailed for a generated digest.
   - Good: strong visual hierarchy, accessible skip link, responsive table/card breakpoints, and consistent escaping for scraped text.

2. The biggest quality regression I found was the archive teaser parser drift.
   - That is fixed in code, but the currently checked-in `docs/index.html` will stay stale until the next render.

3. Markdown output was mixing HTML anchor markup into executive-summary bullets.
   - This is now normalized to plaintext in markdown by stripping tags before writing bullets.

## Validation

Ran:

```bash
python3 -m compileall db.py discovery.py ingest.py main.py pipeline_store.py render_from_store.py scraper.py server.py source_cache.py test_render.py update_digests.py
```

Spot-checked:

- `generate_index(...)` now parses the newer `2026-03-09` mover/decline teaser format correctly.
- `generate_markdown(..., report_date=..., generated_at=...)` now stamps the expected snapshot date/time.
