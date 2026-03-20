# ShooterDigest: Stitch Cowork Instructions

> These are instructions for Stitch's Cowork agent to execute autonomously.
> After each prompt, Cowork should generate the screen AND export the HTML/CSS.
> The exported code gets fed back into Claude Code for implementation in `main.py`.

---

## How This Works (Cowork <-> Claude Code Pipeline)

1. **Cowork generates** each screen in Stitch based on the prompts below
2. **After generating each screen**, Cowork exports the code (Export > Code)
3. **Copy the exported HTML/CSS** into a file at `ShooterDigest/stitch_exports/` (e.g. `grid.html`, `detail_card.html`)
4. **Claude Code reads** those exports and maps the design patterns (CSS variables, class names, layout structure) into the `generate_html()` function in `main.py`
5. **Claude Code verifies** against `STITCH_DESIGN_SPEC.md` that every `[ ]` element is covered

### What Cowork Should Produce Per Screen

For each screen below, export and provide:
- The **full HTML source** (from Export > Code)
- A list of **CSS custom properties** (colors, fonts, spacing) used
- The **component structure** (what classes map to what sections)
- Any **SVG patterns** (sparklines, progress bars, charts) as reusable snippets

---

## PROMPT 1: Updated Intelligence Grid

**Goal:** The main ranking table with ALL columns fully populated.

**Context for Cowork:** This is a data-dense ranking table for 16 competitive FPS games. It's the centerpiece of a weekly analytics digest. The design language is "Bloomberg Terminal meets ESPN." Dark theme, monospace numbers, green accents for positive data, red for negative.

**Design system:**
- Background: #0D0D0F (page), #1A1A1E (cards/rows)
- Text: #F0F0F2 (primary), #808088 (muted), #44444C (dim)
- Accents: #22C55E (green/positive), #EF4444 (red/negative), #F59E0B (amber/neutral), #6366F1 (indigo/primary)
- Fonts: DM Serif Display (headings), Inter (body), JetBrains Mono (numbers/data)

**Required columns per row (this is the COMPLETE set, do not omit any):**

| # | Column | Content | Styling |
|---|--------|---------|---------|
| 1 | RANK | 2-digit monospace (01, 02) | JetBrains Mono, dim color |
| 2 | GAME NAME | Bold title + inline badges: genre pill (colored by genre), lifecycle tag (LIVE/MAINTENANCE/SUNSET/LEGACY with colored outline), sentiment dot (green triangle / red square / gray diamond) | Inter bold for name, small pills after |
| 3 | STEAM CCU | peak_24h with commas (1,421,802) | JetBrains Mono, primary color |
| 4 | EST. TOTAL | Abbreviated (1.42M, 842K) | JetBrains Mono, #22C55E green, bold |
| 5 | WoW TREND | Arrow + percentage: "▲ +4.2%" | Colored by direction: green/red/amber |
| 6 | SPARKLINE | 48x14px inline SVG polyline, 4 data points | Color matches trend direction |
| 7 | ALL-TIME PEAK | Formatted with commas | JetBrains Mono, muted color #808088 |
| 8 | % OF PEAK | Horizontal progress bar (0-100%) + label | Bar fill: green >60%, amber 30-60%, red <30% |
| 9 | STATUS | Pill badge: SURGING/GROWING/STABLE/SLIDING/FADING | Green-to-red spectrum, white text |
| 10 | PLATFORM | Steam share text | Small, gray, Inter |

**Genre colors:**
- Battle Royale: #3B82F6 (blue)
- Tactical: #22C55E (green)
- Hero Shooter: #A855F7 (purple)
- Extraction: #F97316 (orange)
- Arena: #06B6D4 (cyan)
- Large-Scale: #EAB308 (yellow)
- Looter Shooter: #EC4899 (pink)

**Status badge colors:**
- SURGING: bg #22C55E
- GROWING: bg #16A34A
- STABLE: bg #F59E0B
- SLIDING: bg #EF4444
- FADING: bg #DC2626

**Populate first 8 rows with realistic data. Rows 9-16 show "DATA STREAM PENDING" empty state.**

**After generating: Export the HTML/CSS code. Note the class names used for each column so Claude Code can map them to Jinja template variables.**

---

## PROMPT 2: Executive Summary (All Subsections)

**Goal:** The briefing section that sits between the masthead and the grid.

**Required subsections (ALL must be present, stacked vertically):**

**A. Masthead:**
- "TACTICAL INTEL" brand, "Week of March 17, 2026" date, "Steam-only data" caveat banner

**B. Executive Takeaways:**
- 4-5 bullet points with hyperlinked game names (green underline)
- e.g. "Counter-Strike 2 surges +4.2% WoW as Operation Hydra drives peak above 1.4M"

**C. Winners / Neutrals / Losers:**
- 3-column equal-width layout
- Headers: "WINNERS" (#22C55E), "NEUTRALS" (#F59E0B), "LOSERS" (#EF4444)
- 3 rows each: game name + wow_pct in monospace
- e.g. Winners: "Destiny 2 +24.5%", "Counter-Strike 2 +4.2%", "PUBG +3.1%"

**D. Top Movers:**
- 2 cards side by side (~600px each)
- "BIGGEST GAINER" (green left border): game name, "+24.5%", "168,230 -> 410,000", catalyst text
- "BIGGEST DECLINE" (red left border): same layout with decline data

**E. Genre Filter Tabs:**
- Horizontal pill buttons: ALL (16) | BATTLE ROYALE (3) | TACTICAL (2) | etc.
- Active: filled genre color + white text. Inactive: outlined, gray text.

**F. Status Badge Legend:**
- Horizontal row: SURGING | GROWING | STABLE | SLIDING | FADING in their colors
- Caption: "Based on week-over-week player count change"

**G. Aggregate Market Sparkline:**
- 600x80px SVG area chart, 6 months, green fill
- Month labels on x-axis, last value labeled "4.82M total concurrent"
- Title: "AGGREGATE_MARKET_TRAJECTORY"

**After generating: Export code. Identify the HTML structure for each subsection (A-G) so Claude Code can populate them with real data from the pipeline.**

---

## PROMPT 3: Game Detail Card (Fully Populated CS2)

**Goal:** The expanded view when clicking a game row. This is the most complex screen. Every field must be present.

**Use Counter-Strike 2 as the example. Required sections:**

**Header block:**
- Title "Counter-Strike 2" + [TACTICAL] genre pill + [LIVE] lifecycle badge + [SURGING] status pill
- Trend: "▲ +4.2% WoW"
- Context: "All-time peak 1.8M (Feb 2025), currently at 78.9%"
- Catalyst: "Operation Hydra + Competitive Season 4 driving engagement"
- Dev comms flags row: NEW SEASON (green), NEW CONTENT (green), BALANCE CHANGES (green), BUG FIXES (green, "14 fixes"), UPCOMING (gray, "Major qualifier Apr 2026")

**Stats row (monospace, horizontal):**
"24h Peak: 1,421,802 (Steam) | Est. Total: 1.42M (100% Steam) | All-Time Peak: 1,802,853 (78.9% current)"

**Large sparkline:** 700x80px SVG, 12 months, labeled axes, green area fill

**Structured takeaway (4 labeled blocks, stacked):**
- STATE [yellow #F59E0B]: player trend description
- CONTEXT [gray #808088]: why the trend is happening
- COMMUNITY [green #22C55E]: Reddit/press sentiment summary
- OUTLOOK [blue #6366F1]: forward-looking prediction
- Previous week comparison below in gray italic

**2-column layout:**
- Left "Developer Updates": 3 items with sentiment dot, title, date, [PATCH] badge, 2-line summary
- Right "Press Coverage": 4 items with sentiment dot, title, [SOURCE] colored tag, date

**Community Pulse (collapsible):**
- Header: "r/GlobalOffensive, 47 substantive posts"
- 2 columns: THIS WEEK (5 posts) and THIS MONTH (5 posts)
- Each post: [CATEGORY] colored badge + sentiment dot + title + upvote score
- Category colors: NEWS (blue), CRITICISM (red), PRAISE (green), CLIP (purple), DISCUSSION (gray), HUMOR (yellow)
- Top comment preview indented below first 2 posts

**Twitch row:**
"TWITCH: 142,300 viewers | 3,241 streams | 18.2% of total viewership"
Top streams: "s1mple (24,100), gaules (18,200), BLAST (12,400)"

**After generating: Export code. This is the most important export because it contains the most complex component structure. Document every section's class names and nesting.**

---

## PROMPT 4: Genre Rollup + Methodology + Footer

**Goal:** Bottom-of-page sections.

**Genre Rollup Table:**
- Title: "GENRE_ROLLUP // SECTOR ANALYSIS"
- Columns: Genre | Games | Avg 24h Peak | Total Players | Avg WoW Trend
- 7 rows with genre-colored left borders
- Trend column colored by direction

**Methodology (collapsible, starts collapsed):**
- Title: "METHODOLOGY // PLATFORM EXTRAPOLATION"
- Table: Game | Steam Share | Multiplier | Notes
- 16 rows for all tracked games
- Disclaimer text below

**Footer:**
- "DATA_LAST_SYNC: 2026-03-17T08:00:00Z" | "POWERED BY SHOOTERDIGEST // v2.4.0" | source links
- Disclaimer paragraph

**After generating: Export code.**

---

## PROMPT 5: Mobile Responsive (390px)

**Goal:** Mobile versions of the 3 main sections.

**Mobile Grid:** Table becomes card stack. Each card: rank + name + genre badge + status on line 1, CCU + Est Total on line 2, trend + sparkline on line 3, % of peak bar on line 4.

**Mobile Detail Card:** Single column. Stats wrap. Sparkline full width. Dev Updates and Press stack vertically. Community Pulse columns stack. Twitch wraps.

**Mobile Executive Brief:** WNL columns stack vertically. Top Mover cards stack. Genre tabs horizontal scroll. Sparkline full width.

**After generating: Export code. Focus on the CSS media queries and breakpoint patterns.**

---

## After All Screens Are Generated

### For Cowork to do:
1. Export all 5 screens as HTML/CSS code
2. Save exports to `ShooterDigest/stitch_exports/` directory:
   - `01_grid.html`
   - `02_executive_brief.html`
   - `03_detail_card.html`
   - `04_genre_methodology.html`
   - `05_mobile.html`

### For Claude Code to do (next session):
1. Read all 5 exported HTML files
2. Extract the CSS design system (variables, classes, patterns)
3. Map each HTML section to the corresponding `generate_html()` data fields
4. Rebuild the `generate_html()` function in `main.py` using the Stitch design
5. Verify against `STITCH_DESIGN_SPEC.md`, marking all elements as `[x]`
6. Test locally with real data to confirm all fields populate
7. Deploy to Railway

### Verification checklist for Cowork:
Before declaring a screen done, verify it includes these counts:
- Grid: 10 columns visible per row
- Executive Brief: 7 subsections (A through G)
- Detail Card: 7 major sections (header, stats, sparkline, takeaway, dev/press, community, twitch)
- Genre Rollup: 7 genre rows + methodology table + footer
- Mobile: 3 responsive layouts
