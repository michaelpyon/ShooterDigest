# ShooterDigest: Suggestions and Findings

Audit date: 2026-05-30. Builds on the March 2026 code audit (see CHANGES.md).

---

## Evangelist Profile

The ideal evangelist is a competitive FPS player who frequents r/competitivefps and follows multiple game subreddits (r/GlobalOffensive, r/VALORANT, r/apexlegends). They are tired of keeping tabs on five different game subreddits manually and want one weekly "state of the meta" snapshot. They currently check SteamCharts for numbers, browse each subreddit separately, and maybe follow a few esports news sites. They screenshot ShooterDigest when a game they have been defending or writing off suddenly moves sharply in the rankings, and they share it with the caption "called it" or "welp." They bounce in 5 seconds if the page looks like a dev tool or if the numbers look fake; the "Sample briefing" label keeps them on the page just long enough to understand what live data would look like, but only if the overall design reads as credible and intentional.

---

## Ground-Truth Findings (repo HEAD vs. live)

### What is working and honest

1. The sample data fallback is labeled clearly. The home page shows "Sample briefing: Tue, May 26" and "Showing a sample of last week's briefing. Live data refreshes every Monday once the pipeline runs." The title detail pages show "Sample briefing. Live data refreshes every Monday once the pipeline runs." No false claim that the data is live.

2. The footer says "Data from Steam Web API, Reddit, and Google News." This is accurate: that is exactly what the real pipeline uses (see `app/src/pipeline/`). No fabricated authoritative claims.

3. The methodology page correctly describes the scoring model (50% Steam players, 30% Reddit, 20% News), the limited-data reweighting, and the update schedule. No invented claims.

4. The prior audit (March 2026) fixed the Python pipeline: server file exposure, retry policies, CI matrix, archive teaser parser, and historical re-render dates. Those fixes are in HEAD and have been pushed to origin.

5. Live site (https://shooter-digest.vercel.app) matches repo HEAD. The Next.js app is deployed and serving the sample briefing correctly.

### Issues found and fixed this pass

6. Sample news headline URLs were `example.com` placeholders. On the live `/title/[slug]` pages, the "Recent News" section showed clickable links (with real source names like "Dexerto", "PC Gamer") that led to `example.com` dead ends. This eroded trust from the evangelist who clicks a headline expecting an article. Fixed in this pass: all 12 `example.com` URLs in `app/src/lib/sample-data.ts` replaced with Google News search URLs keyed to the article topic, so clicking a sample headline finds real coverage on the same topic.

### Remaining integrity notes (not fixed, lower risk)

7. Sample player counts (e.g. CS2: 1,142,380 concurrent) are representative but not tied to any real fetched value. The page labels them as sample data, so there is no false claim. Risk: if a first-time visitor does not read the small disclaimer, they may take the numbers as live. Mitigation already in place: the label is present.

8. Reddit post URLs in sample data point to the subreddit root (e.g. `https://reddit.com/r/GlobalOffensive`) rather than specific posts. These are accurate: they open the actual subreddit. Not broken, but clicking "The new VAC update actually banned a cheater" and landing at the subreddit homepage is still jarring. No fix attempted (no deploy verification possible).

---

## Prioritized Plan

### Quick wins (S effort, build-verifiable, deploy to see)

1. **[DONE] Fix sample news headline dead links** (app/src/lib/sample-data.ts). Replace 12 `example.com` URLs with Google News search URLs. Live fix: clicking a sample headline now reaches relevant real coverage instead of a 404. S effort, committed this pass.

2. **Add "Sample" label to the Recent News section heading on title pages** (app/src/app/title/[slug]/page.tsx, SampleTitlePage component). Currently the heading just says "Recent News" with no qualifier. A small "(sample)" suffix next to the section heading would prevent the "why does this link not work" reaction even before the user clicks. Change: `Recent News (sample)` when rendering SampleTitlePage. S effort, deploy-needed to verify.

3. **Sample Reddit post URLs: use actual post URL format or clearly label them** (app/src/lib/sample-data.ts). The post links go to subreddit roots, not specific posts. Could replace with `https://reddit.com/r/<sub>/search/?q=<encoded title>` so clicking finds related posts. S effort.

4. **Update SAMPLE_LAST_UPDATED to match or be close to actual deploy date** (app/src/lib/sample-data.ts). Currently hardcoded `2026-05-26T13:00:00.000Z`. If this date gets stale over time (e.g. by September it says "May 26") it signals neglect to the evangelist. S effort: could be set at build time or updated on each significant deploy.

5. **Methodology: tracked titles list vs. pipeline titles list** (app/src/app/methodology/page.tsx). The methodology page lists 12 titles. The live sample data shows only 6. The titles.ts config has more entries (including Escape from Tarkov, Rainbow Six Siege, Hunt: Showdown 1896, Deadlock, PUBG). When the pipeline runs these will appear. The mismatch is confusing but not harmful. Medium effort: add a note that the full set appears once the pipeline has run.

### Medium bets (M effort)

6. **Wire the compare page to sample data** (app/src/app/compare/page.tsx). The compare page fetches `/api/titles` which returns DB data. With no DB, it shows an empty selector and a "select 2 titles" prompt with no options. The evangelist who clicks "Compare" immediately bounces. Fix: return the sample titles list from `/api/titles` when DB is empty (same pattern as the home page fallback). M effort, deploy-needed.

7. **RSS feed returns empty when DB is not connected** (app/src/app/api/rss/route.ts). An evangelist subscribing via RSS gets an empty feed until the pipeline runs. Fix: serve a sample RSS item noting the digest frequency when no DB data exists. M effort.

8. **Subscribe form: no confirmation email** (app/src/app/api/subscribe/route.ts, resend dependency present). The pipeline uses Resend for digest emails, but the subscribe endpoint only writes to DB. There is no "you're subscribed, first digest comes Monday" confirmation email sent on signup. Low priority but improves trust. M effort, needs Resend key in prod.

### Bigger bets (L effort, outside game-tier scope)

9. Connect the live pipeline to the Vercel deployment. Currently the Python pipeline (Railway/Docker) writes to Postgres, but the Next.js app (Vercel) needs to point at the same DB to show live data. The Vercel env var DATABASE_URL likely is not set, which is why the sample fallback is always shown. This is an infra connection task, not a code task.

10. Add a banner or timestamp on the home page that counts down to the next Monday pipeline run, so the evangelist understands exactly when fresh data arrives.

---

## Deploy status note

Prior audit commits (March 2026, fixes 1-8 in CHANGES.md) are in origin/main but the Python pipeline changes are backend-only and do not affect the Vercel Next.js build. The live Vercel site is already serving the correct Next.js HEAD. The sample-data fix committed this pass will go live on Vercel's next build trigger from the push.
