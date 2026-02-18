# Shooter Digest

Weekly competitive shooter player tracker. Scrapes Steam concurrent player data and generates a formatted markdown digest.

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
python main.py
```

Output is saved to `output/digest_YYYY-MM-DD.md`.

## Data Source

Player data is sourced from [SteamCharts](https://steamcharts.com), which tracks Steam concurrent player counts. The script collects 24-hour peak and all-time peak values for each game.

## Project Structure

```
shooter-digest/
├── scraper.py          # SteamCharts scraping functions
├── main.py             # Main script
├── requirements.txt    # Dependencies
├── README.md           # This file
└── output/
    └── digest_YYYY-MM-DD.md
```
