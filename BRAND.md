# BRAND.md - ShooterDigest

## Positioning line (in Dario's language)

**"The weekly ranking of every shooter that matters. Bring receipts, not vibes."**

Secondary: "Is your game dying? Check the chart before you post."

## What the brand is

An intelligence desk for the shooter landscape. HLTV authority tone applied to the whole genre, not 1 esport. It should feel like the page pro analysts would cite, while being written for the guy arguing in a Discord at 1 AM. Confident, numeric, slightly dry. The data is the personality.

## Palette direction

Keep and commit to the existing dark terminal base; do not lighten it.

- Base: near-black `#0a0a0a` background, `#131313` surfaces, hairline borders around `#2a2a2a`
- Text: warm off-white `#e5e2e1`, muted grays for secondary
- Signal colors carry all meaning: green `#4ae176` strictly for up/positive, a red/coral in the `#ffb3ad` family strictly for down/negative, blue `#adc6ff` / `#4d8eff` as the single brand accent (links, active states, score highlights)
- Rule: color only ever encodes data direction or interactivity. No decorative gradients, no colored section backgrounds, no glow

## Type system

- **Inter** stays for UI and body (already loaded)
- Add a **tabular/mono treatment for every number**: player counts, scores, deltas use `font-variant-numeric: tabular-nums` or a mono face (JetBrains Mono / Geist Mono) so columns align and screenshots read as data, not marketing
- Scale: 1 big moment per page (the H1 or the featured score), then a tight 12 to 16px data range. Headlines set tight, semibold, no display fonts

## Spacing and motion personality

- Dense but ordered: SteamDB density with modern breathing room; 4px base grid, generous row height (44 to 52px) so mobile taps land
- Motion is minimal and informational: number count-ups on first paint (under 600ms), sparkline draw-in, a subtle row highlight on rank changes. Nothing bounces, nothing floats, no parallax, no hero animation loops
- Page transitions instant; this is a terminal, not a portfolio piece

## Voice and tone rules

1. Lead with the number, then the sentence: "CS2: 1.14M peak, up 1.8. Still the market." not "CS2 continues to impress!"
2. Analyst dry, never hype. Banned words: unlock, supercharge, insights, revolutionize, game-changing
3. Allowed 1 wink per page max, in Dario's dialect ("the subreddit disagrees")
4. Honesty is voice: "Limited data" and "sample briefing" labels are stated plainly, never hidden in tooltips
5. Weekly cadence is the ritual: everything is framed as "this week's briefing," dated, and archived

## 3 taste references to measure against

1. **SteamDB** - information density, instant load, credibility through restraint
2. **HLTV.org rankings page** - the screenshot-able authority table with movement arrows
3. **Leetify** - modern dark FPS analytics that still feels premium and personal

## 3 anti-references (never look like this)

1. **Tracker.gg / op.gg ad-choked stat sites** - banner ads, popups, content shoved below ad units
2. **Generic AI-template SaaS landing** - purple gradient hero, 3 feature cards with emoji icons, "Get Started" buttons for a product with nothing behind them
3. **Corporate BI dashboard (Tableau/PowerBI embed energy)** - filter sidebars, dropdown soup, gray chrome; this is an editorial ranking with charts, not a self-serve analytics tool
