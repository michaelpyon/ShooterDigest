# ShooterDigest: Stitch Design Spec

> Master checklist for ensuring every data field and UI element from the production template
> is represented in the Stitch designs. Use this for section-by-section review each session.
>
> Status key: `[ ]` not designed, `[~]` partially designed, `[x]` fully designed and reviewed

---

## Session Log

| Date | What happened | Decisions made |
|------|--------------|----------------|
| 2026-03-18 | Initial Stitch prompt with full data model. Generated Core Intelligence Grid v1, Executive Brief, Detailed Intel View, updated footers. | War room aesthetic confirmed. DM Serif Display + Inter + JetBrains Mono. Dark theme #0D0D0F base. Green/red/amber signal colors. |

---

## Section 1: Site Chrome & Navigation

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Sticky nav bar | static | Back button + ShooterDigest logo | [x] TACTICAL INTEL masthead with nav tabs |
| Page title | `week_label` | "ShooterDigest — Week of {date}" | [~] Shows "The Kinetic Ledger" editorial title, not the date-stamped digest title |
| Data caveat info box | static | "Steam-only data" disclaimer banner | [ ] Not designed |
| Share on X button | static | Social share CTA | [x] Present in executive brief |

**Review notes:**
- Need the date-stamped "Week of March 17, 2026" subtitle prominently visible
- Data caveat box is important for credibility, don't skip it

---

## Section 2: Executive Summary

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Market takeaways | `exec_takeaways` (4-5 bullet points) | Hyperlinked bullet list | [~] Editorial paragraph exists but not structured as discrete takeaways |
| Winners / Neutrals / Losers table | `wnl_groups` | 3-column mini-table, 3 games each with name + wow_pct | [ ] Not designed |
| Top Movers: Biggest Gainer | `top_gainer` | Green-accented card: game name, wow_pct, prev_peak -> current_peak | [~] Anomaly Detection section shows gainer but missing prev->current comparison |
| Top Movers: Biggest Decline | `top_decliner` | Red-accented card: game name, wow_pct, prev_peak -> current_peak | [~] Same as above |
| Aggregate market sparkline | `agg_sparkline_data` | 240x60px SVG area chart, 6 months total concurrent | [x] "Aggregate Market Trajectory" chart present |
| Status badge legend | static | SURGING / GROWING / STABLE / SLIDING / FADING with colors | [ ] Not designed |
| Genre filter tab bar | `genres_present` | Horizontal buttons: All + per-genre, each with count badge, colored active underline | [ ] Not designed |

**Review notes:**
- Winners/Neutrals/Losers is a key at-a-glance feature, needs its own designed component
- Genre filter tabs are functional (JS filtering), design needs to show active/inactive states
- Status badge legend should appear once, near the top, before the grid

---

## Section 3: Intelligence Grid (Main Ranking Table)

| Column | Data source | Current design | Stitch status |
|--------|------------|----------------|---------------|
| Rank | `rank` | 2-digit number, monospace | [x] Present as 01, 02, etc. |
| Game Name | `name` | Bold title | [x] Present |
| Genre Badge | `genre` | Colored inline badge (per-genre color) | [~] Shows as subtitle text, not a colored badge |
| Lifecycle Badge | computed | LIVE / MAINTENANCE / SUNSET / LEGACY after game name | [ ] Not designed |
| Sentiment Dot | computed from news | Triangle/square/diamond shape in green/red/gray | [ ] Not designed |
| 24h Peak (Steam) | `peak_24h` | Formatted number with commas | [x] "STEAM CCU" column |
| Est. Total 24h | `est_total_24h` | Green highlighted, abbreviated (1.42M) | [x] "ESTIMATED TOTAL" column, green |
| WoW Trend | `wow_pct` | Arrow + percentage, colored green/red/amber | [x] "WEEKLY TREND" column |
| Mini Sparkline | `avg_trend` (4 points) | 48x14px inline SVG polyline | [x] "MOM MOMENTUM" column |
| All-Time Peak | `peak_all` | Formatted number | [ ] Not in grid |
| % of All-Time Peak | `pct_all` | Progress bar (0-100%) with percentage label | [ ] Not designed |
| Status Label | computed from wow_pct | SURGING/GROWING/STABLE/SLIDING/FADING badge | [ ] Not designed |
| Annotation Icon | big mover flag | Info icon with hover tooltip explaining catalyst | [ ] Not designed |
| Platform Share | `steam_share` | Text like "PC-EXCLUSIVE (100%)" | [x] "PLATFORM SHARE" column |
| Sortable columns | JS | Click column header to sort | N/A (visual design only) |
| Genre CSS class | `genre` | Hidden class for JS genre filtering | N/A (visual design only) |

**Review notes:**
- Grid is missing 3 critical columns: All-Time Peak, % of Peak progress bar, Status Label
- Genre badge needs to be a styled pill/tag, not just subtitle text
- Lifecycle badges and sentiment dots add important context at the row level
- Games 09-16 show "DATA STREAM PENDING" which is a nice empty state, but all 16 should show full data in the design

---

## Section 4: Game Detail Card (Expanded View)

This is the most data-dense section. Each game gets a collapsible card.

### 4a: Card Header

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Game title | `name` | Large bold text | [~] Present in detailed view but as page-level header, not per-card |
| Genre badge | `genre` | Colored pill | [ ] Not visible in detail card |
| Lifecycle badge | computed | LIVE/MAINTENANCE/SUNSET/LEGACY | [ ] Not designed |
| Trend badge | `wow_pct` | Arrow + percentage + "WoW" label | [ ] Not visible in detail card |
| Status label | computed | SURGING/GROWING/etc badge | [ ] Not designed |
| Historical context | computed | e.g. "Peak 100K at launch, now sub-5K" callout | [ ] Not designed |
| Event annotation | `headline_catalyst` | Callout for big movers with catalyst phrase + link | [ ] Not designed |

### 4b: Stats Row

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| 24h Peak (Steam) | `peak_24h` | "24h Peak: 1,421,802 (Steam)" | [ ] Not visible as structured stat row |
| Est. Total | `est_total_24h` + `steam_share` | "Est. Total: 1.42M (100% Steam)" | [ ] |
| All-Time Peak | `peak_all` + `pct_all` | "All-Time Peak: 1,802,853 (78.9% current)" | [ ] |
| Large sparkline | `months` (12 data points) | 240x55px SVG area chart with month labels, last value labeled | [ ] Not designed |

### 4c: Structured Takeaway

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| State | `takeaway_structured.state` | Yellow label + text | [ ] Not designed |
| Context | `takeaway_structured.context` | Gray label + text | [ ] Not designed |
| Community | `takeaway_structured.community` | Green/red label (based on sentiment) + text | [ ] Not designed |
| Outlook | `takeaway_structured.outlook` | Blue label + text | [ ] Not designed |
| Previous week takeaway | `prev.takeaway` | Gray italic text below current | [ ] Not designed |

### 4d: Developer Updates (Left Column)

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Section header | static | "Developer Updates" with sentiment legend | [ ] Not designed |
| News item (x3) | `news[]` | Sentiment dot + linked title + date + patch badge + 2-line summary | [ ] Not designed |
| Patch badge | `news[].is_patch` | Small "PATCH" tag on patch/hotfix items | [ ] Not designed |
| News summary | extracted from `news[].contents` | 2-3 sentences, max 280 chars | [ ] Not designed |
| Dev comms flags | `dev_comms` | Icons/badges for: new season, new content, balance changes, bug fixes, upcoming event | [ ] Not designed |

### 4e: Press Coverage (Right Column)

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Section header | static | "Press Coverage" with sentiment legend | [ ] Not designed |
| Article item (x4) | `external_news[]` | Sentiment dot + linked title + colored source tag + date | [ ] Not designed |
| Source tag | `external_news[].source` | Colored badge per outlet | [ ] Not designed |

### 4f: Community Pulse (Collapsible)

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Section header | `subreddit` + post count | "r/{subreddit} -- {n} substantive posts" | [ ] Not designed |
| This Week column | `reddit_week[]` (5 posts) | Category badge + sentiment dot + linked title + score | [ ] Not designed |
| This Month column | `reddit_month[]` (5 posts) | Same layout as This Week | [ ] Not designed |
| Category badge | `reddit[].category` | Colored pill: NEWS (blue), CRITICISM (red), PRAISE (green), CLIP (purple), DISCUSSION (gray), HUMOR (yellow) | [ ] Not designed |
| Top comment preview | `reddit[].top_comments[0]` | Indented: author + comment text (150 chars) + score | [ ] Not designed |

### 4g: Twitch Data

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Twitch viewers | `twitch_viewers` | Viewer count | [ ] Not designed |
| Twitch streams | `twitch_streams` | Stream count | [ ] Not designed |
| Twitch share | `twitch_share` | % of total tracked viewership | [ ] Not designed |
| Top streams | `twitch_top_streams` | List of top streamers (future) | [ ] Not designed |

**Review notes:**
- The detail card is the biggest gap. Stitch generated an editorial-style detail page but it doesn't map to our per-game card structure.
- Need to design ONE fully populated example card (Counter-Strike 2) with every field filled.
- The 4-part structured takeaway is a signature feature, needs distinct visual treatment.
- Community Pulse with Reddit categories is unique to us, needs bespoke design.

---

## Section 5: Genre Rollup

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Genre Rollup table | computed | Columns: Genre, Games Count, Avg 24h Peak, Avg WoW Trend % | [ ] Not designed |
| Per-genre row accent | genre colors | Subtle colored left border or background per genre | [ ] Not designed |

---

## Section 6: Methodology

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Collapsible section | static | Click to expand | [ ] Not designed |
| Methodology table | `steam_share` per game | Columns: Game, Platform Share %, Est. Multiplier, Notes | [ ] Not designed |
| Disclaimer text | static | Steam-only data caveat, extrapolation explanation | [ ] Not designed |

---

## Section 7: Footer

| Element | Data source | Current design | Stitch status |
|---------|------------|----------------|---------------|
| Data freshness timestamp | `generated_at` | "DATA_LAST_SYNC: {timestamp}" | [x] Designed |
| Powered by ShooterDigest | static | Brand signature | [x] Designed |
| Source disclaimers | static | Links to SteamDB, platform notes | [x] Designed |

---

## Section 8: Responsive / Mobile

| Element | Current design | Stitch status |
|---------|----------------|---------------|
| Table -> card stack on mobile | Summary table transforms to labeled cards at 767px | [ ] Not designed |
| Collapsible sections on mobile | Detail cards and methodology collapse | [ ] Not designed |
| 2-column -> 1-column on mobile | News/press columns stack | [ ] Not designed |
| Font size adjustments | Smaller type on mobile | [ ] Not designed |

---

## Coverage Summary

| Section | Total elements | Designed | Partial | Missing |
|---------|---------------|----------|---------|---------|
| Site Chrome | 4 | 1 | 1 | 2 |
| Executive Summary | 7 | 1 | 2 | 4 |
| Intelligence Grid | 14 | 6 | 1 | 7 |
| Detail Card | 28 | 0 | 1 | 27 |
| Genre Rollup | 2 | 0 | 0 | 2 |
| Methodology | 3 | 0 | 0 | 3 |
| Footer | 3 | 3 | 0 | 0 |
| Mobile | 4 | 0 | 0 | 4 |
| **TOTAL** | **65** | **11** | **5** | **49** |

**Current Stitch coverage: ~17% fully designed, ~25% including partials.**

---

## Workflow: How to Use This File

1. **Before each Stitch session:** Open this file, find the sections marked `[ ]`.
2. **Pick 1-2 sections** to focus on per session. Don't try to do everything at once.
3. **Copy the element table** for that section into the Stitch prompt so it knows exactly what fields to include.
4. **After Stitch generates:** Review the output against this checklist. Update statuses.
5. **Log the session** in the Session Log table at the top.
6. **Michael's feedback** gets captured as review notes under each section.
7. **When exporting to code:** Use this as the acceptance criteria. Every `[x]` must be in the final HTML.

### Suggested session order:
1. **Next:** Intelligence Grid (add missing columns: All-Time Peak, pct_all bar, Status Label, genre badges, lifecycle badges)
2. **Then:** Game Detail Card (single fully populated CS2 example)
3. **Then:** Executive Summary (Winners/Neutrals/Losers, genre tabs, status legend)
4. **Then:** Genre Rollup + Methodology
5. **Then:** Mobile responsive versions
6. **Last:** Polish pass across all screens for consistency
