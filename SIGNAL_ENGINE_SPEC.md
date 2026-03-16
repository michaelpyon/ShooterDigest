# Genre-Agnostic Game Health Signal Engine — Architecture Spec

**Date:** 2026-03-15
**Status:** Draft
**Author:** Ron (spec), Claude Code (implementation)

## The Core Problem

ShooterDigest works because Steam gives you one authoritative number: concurrent players. Everything else — narrative, sentiment, context — wraps around that anchor. For cross-platform and non-Steam games, no single authoritative number exists. So the engine needs to do something harder: synthesize 5-8 imperfect signals into a directional health score that's honest about its own confidence.

The architecture has to solve for this from day one, not bolt it on later.

---

## Mental Model: The Health Score

Think of it like a credit score. No single factor is dispositive. The score is a weighted composite. The trend matters more than the absolute number. And the score needs to be explainable — a client should be able to see exactly which signals moved and why.

```
Game Health Score (0-100)
├── Momentum Index (is it growing or shrinking?)
├── Community Vitality (is the community active?)
├── Content Pulse (is the game getting new content?)
└── Creator Attention (are creators making content?)
```

Each sub-index has 1-3 signals feeding it. The weights are genre-configurable.

---

## Signal Registry

The engine's core primitive is a **Signal**. Every data source is a Signal with a standard interface:

```python
class Signal:
    id: str                    # e.g. "steam_concurrent", "twitch_viewers"
    name: str
    source: str                # where data comes from
    cadence: str               # "realtime", "daily", "weekly"
    platform_affinity: list    # ["pc", "console", "mobile", "all"]
    reliability: float         # 0-1, how trustworthy is this signal
    fetch() -> RawSnapshot
    normalize() -> float       # returns 0-100 score
    trend(days=30) -> float    # returns % change
```

You register signals once. Genre configs just reference them by ID and assign weights.

### Starting Signal Registry

| Signal ID | Source | Cadence | Platform | Reliability | API Cost |
|-----------|--------|---------|----------|-------------|----------|
| `steam_concurrent` | SteamDB / Steam API | Realtime | PC | 0.95 | Free |
| `steam_reviews_velocity` | Steam API | Daily | PC | 0.85 | Free |
| `twitch_hours_watched` | TwitchTracker / Twitch API | Daily | All | 0.80 | Free |
| `twitch_channel_count` | TwitchTracker / Twitch API | Daily | All | 0.75 | Free |
| `reddit_post_velocity` | Reddit API | Daily | All | 0.65 | Free |
| `reddit_subscriber_delta` | Reddit API | Weekly | All | 0.70 | Free |
| `youtube_video_velocity` | YouTube Data API | Daily | All | 0.65 | Free tier |
| `youtube_view_velocity` | YouTube Data API | Daily | All | 0.60 | Free tier |
| `appstore_rank` | Sensor Tower free | Daily | Mobile | 0.80 | Free tier |
| `appstore_review_velocity` | App Store | Daily | Mobile | 0.75 | Free |
| `patch_note_frequency` | Game blog / RSS | Weekly | All | 0.70 | Free |
| `job_posting_delta` | LinkedIn | Weekly | All | 0.50 | Free (manual) |
| `activeplayer_estimate` | ActivePlayer.io | Daily | Console/All | 0.45 | Free |
| `google_trends_index` | Google Trends | Daily | All | 0.55 | Free |

Reliability scores inform confidence bounds on the final health score. A score built from three 0.95 signals has tighter confidence than one built from five 0.55 signals. This is shown to clients explicitly.

---

## Genre Config (YAML)

This is what makes the engine genre-agnostic. A genre config is a YAML file that maps signals to sub-indices with weights:

```yaml
genre: shooter_pc
name: PC Shooter
signals:
  momentum:
    steam_concurrent: 0.60
    twitch_hours_watched: 0.40
  community:
    reddit_post_velocity: 0.50
    reddit_subscriber_delta: 0.30
    twitch_channel_count: 0.20
  content:
    patch_note_frequency: 0.70
    steam_reviews_velocity: 0.30
  creator:
    youtube_video_velocity: 0.60
    youtube_view_velocity: 0.40
```

```yaml
genre: console_shooter
name: Console Shooter (no Steam)
signals:
  momentum:
    twitch_hours_watched: 0.50
    activeplayer_estimate: 0.30
    google_trends_index: 0.20
  community:
    reddit_post_velocity: 0.50
    reddit_subscriber_delta: 0.30
    twitch_channel_count: 0.20
  content:
    patch_note_frequency: 0.80
    job_posting_delta: 0.20
  creator:
    youtube_video_velocity: 0.60
    youtube_view_velocity: 0.40
```

```yaml
genre: mobile_shooter
name: Mobile Shooter
signals:
  momentum:
    appstore_rank: 0.60
    appstore_review_velocity: 0.40
  community:
    reddit_post_velocity: 0.40
    youtube_view_velocity: 0.60
  content:
    patch_note_frequency: 1.00
  creator:
    youtube_video_velocity: 0.70
    twitch_hours_watched: 0.30
```

Adding a new genre: write one YAML file. No code changes.

---

## Game Registry

Each tracked game is a config entry — which genre it belongs to, and where to find each signal's data:

```yaml
game_id: destiny_2
name: Destiny 2
studio: Bungie
genre: console_shooter
sources:
  steam_concurrent: 2514517        # Steam App ID (it IS on Steam too)
  twitch_game_id: "140578"
  reddit: DestinyTheGame
  youtube_query: "Destiny 2"
  activeplayer_slug: destiny-2
  rss: https://www.bungie.net/en/News/Rss
```

```yaml
game_id: halo_infinite
name: Halo Infinite
studio: 343 Industries
genre: console_shooter
sources:
  steam_concurrent: 1240440
  twitch_game_id: "514974"
  reddit: halo
  youtube_query: "Halo Infinite"
  rss: https://www.halowaypoint.com/news/rss
```

```yaml
game_id: marvel_rivals
name: Marvel Rivals
studio: NetEase
genre: shooter_pc
sources:
  steam_concurrent: 2767030
  twitch_game_id: "1234567890"
  reddit: MarvelRivals
  youtube_query: "Marvel Rivals"
```

---

## Data Pipeline

Three jobs, clearly separated:

### 1. Ingest (runs on cadence per signal)

```
fetch raw data from source
→ store RawSnapshot (immutable, content-hashed)
→ never mutates historical data
```

### 2. Normalize (runs after ingest)

```
read RawSnapshot
→ apply signal-specific normalization (log scale for concurrents, z-score for velocity)
→ write NormalizedSignalValue
```

### 3. Score (runs on delivery cadence)

```
read NormalizedSignalValues for all signals
→ apply genre config weights
→ compute sub-index scores
→ compute composite Health Score with confidence band
→ write GameHealthSnapshot
```

Render/digest generation only reads from GameHealthSnapshot. Never touches raw data.

### Database Schema

```sql
-- Signal registry (loaded from config, stored for reference)
CREATE TABLE signals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    cadence TEXT NOT NULL,
    reliability FLOAT NOT NULL
);

-- Raw snapshots (immutable append-only log)
CREATE TABLE raw_snapshots (
    id SERIAL PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(id),
    game_id TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_value JSONB NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(signal_id, game_id, content_hash)
);

-- Normalized values (derived from raw snapshots)
CREATE TABLE normalized_values (
    id SERIAL PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(id),
    game_id TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score FLOAT NOT NULL,          -- 0-100
    trend_pct FLOAT,               -- % change vs prior period
    raw_snapshot_id INTEGER REFERENCES raw_snapshots(id)
);

-- Game health snapshots (final composite scores)
CREATE TABLE health_snapshots (
    id SERIAL PRIMARY KEY,
    game_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    health_score FLOAT NOT NULL,   -- 0-100 composite
    confidence FLOAT NOT NULL,     -- 0-1 based on signal reliability
    momentum_score FLOAT,
    community_score FLOAT,
    content_score FLOAT,
    creator_score FLOAT,
    signals_used INTEGER,
    signals_available INTEGER,
    detail JSONB,                  -- full breakdown per signal
    UNIQUE(game_id, snapshot_date)
);

-- Game registry
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    studio TEXT,
    genre TEXT NOT NULL,
    sources JSONB NOT NULL,        -- per-signal source identifiers
    active BOOLEAN DEFAULT TRUE
);
```

---

## Output: What Clients Actually Get

Each week, a client gets:

```
COMPETITOR HEALTH REPORT — Week of March 15, 2026
Genre: Console RPG

[Game Name] Health Score: 72/100 ↑ (+8 from last week)
Confidence: Medium (3 of 5 signals available)

Momentum: 68 ↑  — Twitch hours watched up 22% WoW
Community: 81 ↑  — Reddit post velocity near 6-month high
Content:   65 →  — No patch notes this week (3rd consecutive)
Creator:   74 ↑  — YouTube video count up 15% WoW

Signal Gaps: Steam data not available. ActivePlayer estimate excluded
(low reliability). Score built from: Twitch, Reddit, YouTube, RSS.

Notable: Community vitality spike without content update suggests
organic player-driven moment — worth monitoring.
```

The confidence disclosure is non-negotiable. Clients need to know when the score is built on 2 weak signals vs. 5 strong ones. That's what separates this from the ActivePlayer.io black box that nobody trusts.

---

## The Moat

It's not the data — anyone can scrape Twitch. It's the **genre config layer** and the **confidence-transparent scoring**. A studio can trust a score that tells them exactly which signals it's built from and how reliable each one is. That's the thing nobody else does, and it's the thing that makes a biz ops lead comfortable sharing it in an exec meeting.

Defensible position: not "we have better data," but "we tell you exactly what we know and don't know."

---

## Build Sequence

### Phase 1: Prove the Score (Weeks 1-2)

- Pick 3 signals: Twitch hours watched, Reddit post velocity, YouTube video velocity
- Build fetchers for each, store to Postgres (Railway, already have it)
- Build a simple normalizer that outputs 0-100 per signal
- Hard-code one genre config (console shooter)
- Compute composite score for 3 games: Halo Infinite, Destiny 2, Marathon
- Confirm the score moves in the right direction when you expect it to

### Phase 2: First Digest (Week 3)

- Generate a weekly digest in Markdown using scores
- Integrate into ShooterDigest output (or parallel output)
- Email it to yourself — if it's useful, it's a product

### Phase 3: Expand Signals (Week 4)

- Add Steam concurrents (already have this pipeline)
- Add Google Trends
- Add patch note frequency via RSS
- Tune weights based on Phase 1 observations

### Phase 4: Client-Ready (Weeks 5-6)

- Add genre config loader (YAML)
- Add game registry
- Build a simple dashboard or weekly email delivery
- Beta test with 1-2 contacts

---

## Infrastructure Cost at Launch

| Resource | Cost |
|----------|------|
| Postgres (Railway) | Already have |
| YouTube Data API | Free tier (10K units/day) |
| Reddit API | Free |
| Twitch API | Free |
| Google Trends | Free |
| RSS feeds | Free |
| **Total** | **~$0 additional** |

---

## Relationship to ShooterDigest

ShooterDigest is the first implementation of this engine, using the `shooter_pc` genre config with Steam as the anchor signal. The signal engine doesn't replace ShooterDigest — it generalizes it.

ShooterDigest continues as the public-facing product and proof of concept. The signal engine is the infrastructure that enables genre expansion and B2B client digests.

```
Signal Engine (generic)
├── ShooterDigest (public, shooter_pc config)
├── Console Shooter Digest (B2B, console_shooter config)
├── Mobile Gaming Pulse (B2B, mobile config)
└── [Client-specific] (custom genre config per client)
```

---

## Open Questions

1. **Weight calibration:** How do we validate that the genre config weights produce scores that match expert intuition? Probably manual tuning for the first 2-3 genres, then track divergence.
2. **Anomaly detection:** Should the score engine flag sudden spikes/drops automatically? (e.g., Twitch +300% = major content drop or controversy). Yes, but as a Phase 3 feature.
3. **Historical backfill:** Some signals (Reddit, Twitch) have historical data available. Worth backfilling to establish baselines. Steam data already backfilled.
4. **Rate limiting:** Reddit and YouTube have API quotas. Need per-source rate limit configs. See the shared `provider-budget` pattern from the backend roadmap.
5. **Pricing model:** $200-500/month per studio for weekly digest. $500-1,000/month for daily + custom alerts. Needs validation.
