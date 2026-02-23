# ShooterDigest

Weekly competitive shooter analytics dashboard. Scrapes player data from Steam, Reddit, and Google News for 15+ FPS/BR titles and generates a formatted HTML digest report.

## What it does

- Fetches concurrent player counts from Steam Charts
- Pulls patch notes and news from Steam News API and Google News RSS
- Scrapes Reddit community discussion (r/competitivefps and game-specific subs)
- Generates a timestamped HTML digest (`output/digest_YYYY-MM-DD.html`)
- Serves those digests via a simple HTTP server

## Tech stack

- Python 3.12 — scraping, data processing, server
- BeautifulSoup4 + Requests — scraping
- pandas — trend analysis
- Python's built-in `http.server` — serves static HTML
- Docker + Railway — deployment

## Local dev

```bash
pip install -r requirements.txt
python main.py          # generates output/digest_YYYY-MM-DD.html
python server.py        # serves on port 8080
```

## Key files

- `main.py` — orchestrates the full digest: calls scraper, formats output, writes HTML
- `scraper.py` — all data collection (Steam Charts, Steam News API, Reddit, Google News RSS)
- `server.py` — SimpleHTTPRequestHandler, serves `/output` directory
- `Dockerfile` — runs `main.py` at build time (static generation), then starts `server.py`
- `railway.json` — Railway config, start command: `python server.py`
- `output/` — generated digest HTML files (not committed)
- `nycguy.html` — separate NYC neighborhood diagnostic tool (served at `/nyc`)
- `nyc-neighborhoods.html` — served at `/neighborhoods`
- `massage-app/` — separate Next.js project, unrelated, ignore it

## Deployment

Hosted on Railway. Docker build runs `main.py` to generate the digest statically, then serves it. The digest is baked in at deploy time — it doesn't regenerate dynamically. To get a fresh digest, trigger a redeploy.

## Architecture notes

- Steam player counts are the authoritative source; other sources add context
- `scraper.py` uses `steam_share` fractions to extrapolate cross-platform player estimates
- Heavy text sanitization: strips HTML entities, BBCode, Reddit markdown artifacts
- No database — all state is in generated HTML files
- `/nyc` and `/neighborhoods` routes serve alternate HTML pages (unrelated to shooter data)

## Tracked games

CS2, Valorant, Apex Legends, PUBG, Rainbow Six Siege, Overwatch 2, Marvel Rivals, Call of Duty (Warzone/BO6), Halo Infinite, Delta Force, Arc Raiders, Battlefield 6, and others defined in `main.py`.
