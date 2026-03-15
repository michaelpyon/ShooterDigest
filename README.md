# Shooter Digest

Weekly competitive shooter player tracker. Scrapes Steam concurrent player data, persists a reusable ingest snapshot, and renders formatted digest artifacts from stored data.

## Tracked Games

- Counter-Strike 2
- Apex Legends
- Call of Duty
- Rainbow Six Siege
- Marvel Rivals
- Overwatch
- Battlefield 6
- Delta Force
- Halo Infinite
- Arc Raiders

## Setup

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Usage

```bash
python ingest.py
python render_from_store.py
```

For one-shot local runs, `python main.py` still works and now performs both steps.

Output is saved to:

- `output/digest_YYYY-MM-DD.md`
- `output/digest_YYYY-MM-DD.html`
- `output/pipeline/YYYY-MM-DD.json`

## Data Source

Player data is sourced from [SteamCharts](https://steamcharts.com), which tracks Steam concurrent player counts. The script collects 24-hour peak and all-time peak values for each game.

## Project Structure

```
shooter-digest/
├── scraper.py             # Source fetchers with HTTP caching
├── ingest.py              # Scrape once and store a pipeline snapshot
├── render_from_store.py   # Render digest artifacts from stored snapshot
├── pipeline_store.py      # SQLite-backed snapshot registry
├── main.py                # Shared collection/render helpers + one-shot entrypoint
├── requirements.txt       # Dependencies
├── README.md              # This file
└── output/
    ├── digest_YYYY-MM-DD.md
    ├── digest_YYYY-MM-DD.html
    └── pipeline/
        └── YYYY-MM-DD.json
```
