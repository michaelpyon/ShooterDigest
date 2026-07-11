# DESIGN.md - ShooterDigest source of truth (AAA relaunch)

Companion docs: PERSONA.md (Dario), BRAND.md (voice, palette, references). This file is the build contract. Preserve the product name (ShooterDigest) and core concept: a weekly cross-title health ranking of competitive shooters built from Steam player data, Reddit sentiment, and news volume.

## Design tokens (carried forward from Stitch export)

47 tokens live in `.stitch/design-reference.html`. Canonical core: background `#0a0a0a`, surface `#131313`, text `#e5e2e1`, primary `#adc6ff` / container `#4d8eff`, positive `#4ae176`, negative/tertiary `#ffb3ad`, error `#ffb4ab`, outline `#8c909f`, surface-high `#2a2a2a`. Type: Inter throughout, plus the tabular-numeral rule in BRAND.md.

## Layout / IA intent

Keep the existing route map; deepen it, do not replace it.

- `/` - the ranking. This IS the product and the landing page. No marketing hero above it
- `/title/[slug]` - per-game detail: score history, player trend, sentiment, news items
- `/compare` - 2 to 4 titles side by side
- `/methodology` - the trust page; how the composite score is built, weights, data sources, limits
- `/api/rss` - keep; it is a differentiator for the RSS crowd Dario respects

Nav stays 1 row: wordmark, Compare, Methodology, RSS. Add a "week of" date stamp in the nav or directly above the table so recency is visible before scroll.

## Hero / landing concept

**The table is the hero.** Above it, exactly 3 lines:

1. H1: "Competitive FPS Intelligence" or sharper per BRAND positioning
2. 1-line sub: what the score is (players + sentiment + news, weekly)
3. The briefing status line: date of the data plus its honesty label (see Data honesty)

Then the ranked table immediately, in-viewport on desktop and mobile. Each row: rank, title + genre tag, player count (or "Limited data" for non-Steam titles like Valorant/OW2), sentiment chip, composite score in tabular numerals, weekly delta with ▲/▼, and a 12-week sparkline. Row click goes to `/title/[slug]`.

Newsletter subscribe stays BELOW the table, 1 quiet block, never a modal.

## Key screens list

1. **Ranking (/)** - the weekly table, status line, subscribe block, footer with source attribution
2. **Title detail (/title/[slug])** - score header with delta, 12-week score chart, player trend, sentiment summary, recent news list, share button
3. **Compare (/compare)** - picker plus overlaid sparklines and stat columns
4. **Methodology (/methodology)** - weights, sources, update cadence, known limits (non-Steam titles), plain analyst voice
5. **Share card (OG image)** - not a browsed screen, but a first-class rendered surface (see X-readiness)

## Empty / loading / error state intent

- **No pipeline data (current prod reality):** show the sample briefing with an unmissable but non-apologetic label (see Data honesty). Never show "No data yet. Run the pipeline." to the public again; that is a dev message
- **Loading:** skeleton rows matching final table geometry (rank, name, score columns) so there is no layout shift; target under 1s perceived
- **Partial data:** per-title "Limited data" badge (keep the existing concept) instead of fake zeros. A title with no Steam API never displays an invented player count
- **Error (DB unreachable):** fall back to the newest bundled sample silently plus the sample label; log server-side. The public page must never render a stack trace or an empty table
- **Empty compare:** pre-select 2 sensible defaults (CS2 vs the biggest weekly mover) so the screen is never blank

## Metadata / OG intent (X-readiness is mandatory)

- Root already ships title, description, og:image (og.png 1200x630) and twitter summary_large_image; keep, and make all tags agree on 1 canonical host (decide vercel.app vs shooter.michaelpyon.com via SITE_URL and align og:url, canonical, and twitter tags)
- **Add dynamic per-title OG images** via next/og at `/title/[slug]`: dark card, game name, composite score huge in tabular numerals, weekly delta arrow colored, sparkline, "ShooterDigest - week of {date}" footer. This is the receipts screenshot, generated for him
- Root og:image should be a rendered snapshot of the top 5 ranking, not an abstract logo card, so the X preview shows actual data
- Title pattern: "{Game} health score: {score} ({delta}) | ShooterDigest". Description carries the 1-line analyst read

## The screenshot-worthy moment to engineer

**The rank-flip receipt.** A per-title share affordance (button on the title page plus a row-level action) that produces the OG-style score card: name, score, delta, sparkline, week date. It must read at a glance in a Discord embed and an X preview. Secondary moment: the top-10 table itself, so table styling must survive cropping (clear row borders, and the ShooterDigest wordmark plus week date INSIDE the table container so every screenshot is self-attributed).

## Data honesty (mandatory disclosure)

Current truth as of 2026-07-11: production has no DATABASE_URL and the pipeline has never run in prod. The live site renders hardcoded sample data (app/src/lib/sample-data.ts) dated Tue, May 26, with the copy "Showing a sample of last week's briefing. Live data refreshes every Monday once the pipeline runs."

That copy is **not currently honest**: it is not last week's briefing (6 weeks stale) and no Monday refresh actually happens. Required until the pipeline plus Postgres are wired (.env: DATABASE_URL, reddit, email creds):

1. Label the data "Sample briefing (illustrative data)" with the real sample date; do not imply it was ever a live weekly run
2. Drop the "refreshes every Monday" promise unless a scheduled run genuinely exists; otherwise say "Live weekly runs coming soon"
3. Methodology page states which numbers are real when live (Steam concurrents) and which are modeled (cross-platform estimates via steam_share fractions, per the Python pipeline)
4. Never emit sample sentiment or player counts in share cards without the sample label baked into the image

The moment DATABASE_URL plus a scheduled pipeline run land (the carried-forward bet), the label flips to "Week of {date}" and the countdown-to-next-Monday banner becomes viable.

## Build guardrails

- Stack stays Next.js TS + Prisma + Postgres in app/; the Python pipeline at repo root remains the historical ingest reference. Do not re-architect (standing rule from the rejected V2 rebuild)
- Dark theme only; palette and type per BRAND.md
- Mobile: the table degrades to stacked rows keeping rank, name, score, delta visible without horizontal scroll
- Performance: ranking page server-rendered with revalidate (already 3600s), no client data fetching for the core table
