# Stitch Follow-Up: Add All Missing Data Elements

> Paste this into Stitch as a single prompt. It references the existing Intel Digest design and adds every missing element from our data model.

---

```
The current Intel Digest screen is a great foundation. I need you to update it to include ALL of these missing elements. Keep the exact same design language: #00FF41 matrix green, Newsreader headlines, Space Grotesk labels, Inter body, dark #0e0e0e background, the // prefixed section headers, tracking-widest uppercase labels. Do NOT change the aesthetic, just add the missing data.

ADDITIONS TO THE MAIN TABLE (add these columns to every game row):

After GAME_IDENTIFIER, add inline badges:
- GENRE badge: small colored pill after game name. Colors: Battle Royale=#3B82F6, Tactical=#00FF41, Hero Shooter=#A855F7, Extraction=#F97316, Arena=#06B6D4, Large-Scale=#EAB308, Looter Shooter=#EC4899
- LIFECYCLE badge: tiny outlined tag — LIVE (green outline), MAINTENANCE (amber outline), SUNSET (red outline)
- SENTIMENT dot: small shape — green triangle=positive, red square=negative, gray diamond=neutral

Add these columns after WEEKLY_DELTA:
- ALL_TIME_PEAK: the game's highest-ever concurrent (e.g. "1,802,853"), monospace, dimmer color
- PCT_OF_PEAK: horizontal progress bar showing current as % of all-time. Bar fill: green >60%, amber 30-60%, red <30%. Show percentage label (e.g. "78.9%")
- STATUS: pill badge — SURGING (#00FF41 bg), GROWING (#16A34A bg), STABLE (#F59E0B bg), SLIDING (#EF4444 bg), FADING (#DC2626 bg). White text.

ADD NEW SECTION: EXECUTIVE BRIEF (above the roster matrix):

Between the executive summary and the table, add:

A. WINNERS / NEUTRALS / LOSERS — 3-column layout
- Headers: "WINNERS" (green), "NEUTRALS" (amber), "LOSERS" (red)
- 3 rows each: game name + wow_pct
- Example: Winners column: "Destiny 2 +24.5%", "Counter-Strike 2 +4.2%", "PUBG +3.1%"
- Use the same Space Grotesk labels style

B. TOP MOVERS — 2 cards side by side
- Left: "BIGGEST_GAINER" with green left border. Show: game name, "+24.5%" large, "168,230 → 410,000" (previous → current), catalyst text
- Right: "BIGGEST_DECLINE" with red left border. Same layout with decline data

C. GENRE FILTER TABS — horizontal row of pill buttons
- ALL (16) | BATTLE ROYALE (3) | TACTICAL (2) | HERO SHOOTER (3) | EXTRACTION (2) | ARENA (1) | LARGE-SCALE (2) | LOOTER SHOOTER (1)
- Active: filled with genre color + white text. Inactive: ghost-border style, gray text

D. STATUS LEGEND — single row showing all 5 status badges: SURGING | GROWING | STABLE | SLIDING | FADING
- Caption: "// CLASSIFICATION_BASED_ON_WOW_DELTA"

UPDATE THE EXPANDED DETAIL ROWS (CS2 and Apex):

Keep the 3-column layout but add these missing elements:

Column 1 (Trend & Updates) — add:
- DEV_COMMS_FLAGS: row of small tags — NEW_SEASON (green), NEW_CONTENT (green), BALANCE_CHANGES (amber), BUG_FIXES (gray, "14 deployed"), UPCOMING_EVENT (blue, "Major Qualifier Apr 2026")
- STRUCTURED TAKEAWAY with 4 labeled blocks:
  - STATE [yellow/amber label]: current player trend description
  - CONTEXT [gray label]: why the trend is happening
  - COMMUNITY [green or red label based on sentiment]: Reddit/press sentiment summary
  - OUTLOOK [blue/indigo label]: forward-looking prediction
- PREVIOUS_WEEK line: gray italic text comparing to last week's data

Column 2 (Press & Reddit) — update:
- SIGNAL_MONITORING: add source tags colored by outlet: [HLTV] blue, [IGN] red, [PC_GAMER] orange, [DEXERTO] purple, [THE_VERGE] cyan
- Add sentiment classification: BULLISH (green), BEARISH (red), NEUTRAL (gray) — already have this, keep it
- REDDIT_PULSE: expand to show 5 posts with CATEGORY badges: [NEWS] blue, [CRITICISM] red, [PRAISE] green, [CLIP] purple, [DISCUSSION] gray
- Each post: category badge + title + upvote score
- Show 1 top comment preview under first 2 posts

Column 3 (Media & Stats) — update:
- TWITCH data: show viewers, stream count, AND share % of total viewership
- Add "TOP_STREAMS" list: 3 streamer names with viewer counts
- STATS row below image: "24h Peak: 1,421,802 (Steam) | Est. Total: 1.42M | All-Time: 1,802,853 (78.9%)"

ADD NEW SECTION: GENRE_ROLLUP (below the roster matrix):

- Title: "// GENRE_ROLLUP // SECTOR_ANALYSIS"
- Table: Genre | Games | Avg 24h Peak | Total Players | Avg WoW Trend
- 7 rows with genre-colored left borders
- Numbers in Space Grotesk monospace style

ADD NEW SECTION: METHODOLOGY (collapsible, below genre rollup):

- Title: "// METHODOLOGY // PLATFORM_EXTRAPOLATION"
- Table: Game | Steam Share | Multiplier | Notes
- Show data for all tracked games
- Disclaimer text below

UPDATE FOOTER:
- Left: "DATA_LAST_SYNC: 2026-03-17T08:00:00Z"
- Center: "POWERED BY SHOOTERDIGEST // v2.4.0"
- Right: "STEAMDB | REDDIT_API | GOOGLE_NEWS | TWITCH"

Populate ALL 16 game rows with full data (not just first 2 expanded). At minimum show 8 rows with complete column data, rows 9-16 can show the truncated state.

This should be a single 1280px wide scrollable page. Keep the same war room / intelligence terminal aesthetic throughout.
```
