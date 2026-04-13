export const metadata = {
  title: "Methodology | ShooterDigest",
  description:
    "How ShooterDigest calculates health scores for competitive FPS titles.",
};

export default function MethodologyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-black text-text tracking-tight mb-6">
        Methodology
      </h1>

      <div className="space-y-8 text-text-muted text-sm leading-relaxed">
        {/* Overview */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Overview
          </h2>
          <p>
            ShooterDigest tracks the health of competitive FPS titles using 3
            data sources: Steam player counts, Reddit community activity, and
            Google News coverage. Each title gets a composite health score from 0
            to 100, updated weekly.
          </p>
          <p className="mt-2">
            The score captures whether a game&apos;s ecosystem is growing,
            stable, or declining relative to its own historical baseline. It is
            not a ranking of game quality.
          </p>
        </section>

        {/* Data Sources */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Data Sources
          </h2>

          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-lg p-4">
              <h3 className="text-text font-medium text-sm mb-1">
                Steam Web API (Player Count)
              </h3>
              <p className="text-text-subtle text-xs">Weight: 50%</p>
              <p className="mt-2">
                Current concurrent player count from Steam&apos;s
                ISteamUserStats/GetNumberOfCurrentPlayers endpoint. Compared
                against the title&apos;s 30-day average. A ratio of 1.0 (at
                average) maps to a sub-score of 50. Above average pushes toward
                100; below average pushes toward 0.
              </p>
            </div>

            <div className="bg-surface border border-border rounded-lg p-4">
              <h3 className="text-text font-medium text-sm mb-1">
                Reddit Activity
              </h3>
              <p className="text-text-subtle text-xs">Weight: 30%</p>
              <p className="mt-2">
                Post volume (top 25 posts over the past week) and hot post count
                from each title&apos;s subreddit via the Reddit API. Volume is
                compared against historical average. Sentiment is computed using
                VADER (Valence Aware Dictionary and sEntiment Reasoner) on post
                titles, producing a compound score from -1.0 to +1.0. Positive
                sentiment adds up to +15 points; negative sentiment subtracts up
                to 15.
              </p>
            </div>

            <div className="bg-surface border border-border rounded-lg p-4">
              <h3 className="text-text font-medium text-sm mb-1">
                Google News RSS (News Coverage)
              </h3>
              <p className="text-text-subtle text-xs">Weight: 20%</p>
              <p className="mt-2">
                Article count from Google News RSS search. Filtered for gaming
                relevance (non-gaming articles like sports are excluded).
                Compared against historical average. More coverage relative to
                baseline pushes the sub-score higher.
              </p>
            </div>
          </div>
        </section>

        {/* Score Composition */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Score Composition
          </h2>

          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-3 text-text-subtle text-xs uppercase tracking-widest font-medium">
                    Source
                  </th>
                  <th className="text-right p-3 text-text-subtle text-xs uppercase tracking-widest font-medium">
                    Full Data
                  </th>
                  <th className="text-right p-3 text-text-subtle text-xs uppercase tracking-widest font-medium">
                    Limited Data
                  </th>
                </tr>
              </thead>
              <tbody className="text-text-muted">
                <tr className="border-b border-border/50">
                  <td className="p-3">Player Count</td>
                  <td className="p-3 text-right mono">50%</td>
                  <td className="p-3 text-right mono text-text-subtle">N/A</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="p-3">Reddit Activity</td>
                  <td className="p-3 text-right mono">30%</td>
                  <td className="p-3 text-right mono">60%</td>
                </tr>
                <tr>
                  <td className="p-3">News Coverage</td>
                  <td className="p-3 text-right mono">20%</td>
                  <td className="p-3 text-right mono">40%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Limited Data */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Limited Data Titles
          </h2>
          <p>
            Some titles (Valorant, Escape from Tarkov) don&apos;t have Steam
            player counts because they&apos;re distributed through other
            launchers. For these titles, the player count weight (50%) is
            redistributed proportionally: Reddit becomes 60% and News becomes
            40%.
          </p>
          <p className="mt-2">
            These titles are tagged with a &quot;Limited Data&quot; badge on the
            dashboard and title pages. Cross-comparisons between full-data and
            limited-data titles should account for this difference in signal
            depth.
          </p>
        </section>

        {/* Score Interpretation */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Score Ranges
          </h2>
          <div className="space-y-2">
            {[
              {
                range: "80-100",
                label: "Thriving",
                color: "text-secondary",
                desc: "Above-average player counts, active community, strong news coverage.",
              },
              {
                range: "60-79",
                label: "Healthy",
                color: "text-accent",
                desc: "Solid engagement across most signals. Stable or growing.",
              },
              {
                range: "40-59",
                label: "Neutral",
                color: "text-warning",
                desc: "At or near historical baseline. No strong trend either way.",
              },
              {
                range: "20-39",
                label: "Declining",
                color: "text-[#f97316]",
                desc: "Below-average activity. Possible seasonal dip or sustained decline.",
              },
              {
                range: "0-19",
                label: "Critical",
                color: "text-tertiary",
                desc: "Significantly below baseline across multiple signals.",
              },
            ].map((tier) => (
              <div
                key={tier.range}
                className="flex items-start gap-3 bg-surface border border-border rounded-lg p-3"
              >
                <span className={`mono text-sm font-bold ${tier.color} w-14`}>
                  {tier.range}
                </span>
                <div>
                  <span className={`text-sm font-medium ${tier.color}`}>
                    {tier.label}
                  </span>
                  <p className="text-text-subtle text-xs mt-0.5">{tier.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Pipeline */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Update Schedule
          </h2>
          <p>
            The data pipeline runs weekly (Mondays, 5 AM ET). It fetches fresh
            data from all 3 sources, computes scores, and writes weekly
            snapshots. The email digest goes out at 8 AM ET the same day.
          </p>
          <p className="mt-2">
            Historical trends are built from these weekly snapshots. The more
            weeks of data available, the more accurate the trend baselines
            become.
          </p>
        </section>

        {/* Tracked titles */}
        <section>
          <h2 className="text-text font-semibold text-base mb-3">
            Tracked Titles
          </h2>
          <p>
            ShooterDigest tracks 12 competitive FPS titles selected based on
            Steam availability, active subreddit communities (50k+ members), and
            competitive relevance:
          </p>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[
              "Counter-Strike 2",
              "Valorant *",
              "Apex Legends",
              "Overwatch 2",
              "Rainbow Six Siege",
              "Escape from Tarkov *",
              "Hunt: Showdown 1896",
              "The Finals",
              "Marvel Rivals",
              "Deadlock",
              "PUBG: Battlegrounds",
              "Call of Duty",
            ].map((title) => (
              <span
                key={title}
                className="text-text-muted text-xs bg-surface border border-border rounded px-2.5 py-1.5"
              >
                {title}
              </span>
            ))}
          </div>
          <p className="text-text-subtle text-xs mt-2">
            * Limited Data: no Steam player count available.
          </p>
        </section>

        {/* Contact */}
        <section className="border-t border-border pt-6">
          <p className="text-text-subtle text-xs">
            Questions about the methodology? Reach out at{" "}
            <a
              href="mailto:michael@michaelpyon.com"
              className="text-accent hover:underline"
            >
              michael@michaelpyon.com
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
