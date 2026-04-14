import { notFound } from "next/navigation";
import { prisma } from "@/lib/db";
import { ScoreBadge, ChangeIndicator } from "@/components/score-badge";
import { Sparkline } from "@/components/sparkline";
import { formatNumber } from "@/lib/utils";
import Link from "next/link";

export const revalidate = 3600;

interface TitlePageProps {
  params: Promise<{ slug: string }>;
}

async function getTitleData(slug: string) {
  const title = await prisma.title.findUnique({
    where: { slug },
    include: {
      scores: {
        orderBy: { date: "desc" },
        take: 2,
      },
      snapshots: {
        orderBy: { weekOf: "desc" },
        take: 12,
      },
      playerData: {
        orderBy: { date: "desc" },
        take: 12,
      },
      redditData: {
        orderBy: { date: "desc" },
        take: 1,
      },
      newsData: {
        orderBy: { date: "desc" },
        take: 1,
      },
    },
  });

  return title;
}

export default async function TitlePage({ params }: TitlePageProps) {
  const { slug } = await params;

  let title;
  try {
    title = await getTitleData(slug);
  } catch {
    // DB not connected
  }

  if (!title) {
    notFound();
  }

  const currentScore = title.scores[0];
  const previousScore = title.scores[1];
  const change =
    currentScore && previousScore
      ? currentScore.compositeScore - previousScore.compositeScore
      : null;

  const hasSteamData = title.steamAppId != null;
  const sparklineData = title.snapshots
    .map((s) => s.compositeScore)
    .reverse();

  const latestPlayer = title.playerData[0];
  const latestReddit = title.redditData[0];
  const latestNews = title.newsData[0];

  // Parse JSON data safely
  let topPosts: Array<{
    title: string;
    url: string;
    score: number;
    commentCount: number;
    date: string;
  }> = [];
  let topHeadlines: Array<{
    title: string;
    url: string;
    source: string;
    date: string;
  }> = [];

  try {
    if (latestReddit?.topPostsJson) {
      topPosts = JSON.parse(latestReddit.topPostsJson);
    }
  } catch {
    /* invalid JSON */
  }

  try {
    if (latestNews?.topHeadlinesJson) {
      topHeadlines = JSON.parse(latestNews.topHeadlinesJson);
    }
  } catch {
    /* invalid JSON */
  }

  // Player count history for chart
  const playerHistory = title.playerData
    .map((p) => ({
      date: p.date.toISOString().slice(0, 10),
      players: p.currentPlayers,
    }))
    .reverse();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/"
          className="text-text-subtle hover:text-text text-sm transition-colors"
        >
          Dashboard
        </Link>
        <span className="text-border-hover mx-2">/</span>
        <span className="text-text-muted text-sm">{title.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-text tracking-tight">
              {title.name}
            </h1>
            {!hasSteamData && (
              <span className="text-xs font-medium text-warning bg-warning/10 px-2 py-1 rounded">
                Limited Data
              </span>
            )}
          </div>
          <p className="text-text-subtle text-sm mt-1">
            {title.genreTags[0] ?? "FPS"}
            {title.launchDate &&
              ` | Launched ${title.launchDate.toLocaleDateString("en-US", { month: "short", year: "numeric" })}`}
          </p>
        </div>
        <div className="text-right">
          <ScoreBadge score={currentScore?.compositeScore ?? 0} size="lg" />
          <div className="mt-2">
            <ChangeIndicator change={change} />
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <ScoreCard
          label="Player Count"
          score={currentScore?.playerScore ?? null}
          detail={
            latestPlayer
              ? `${formatNumber(latestPlayer.currentPlayers)} current`
              : hasSteamData
                ? "No data yet"
                : "Not available on Steam"
          }
          available={hasSteamData}
        />
        <ScoreCard
          label="Reddit Activity"
          score={currentScore?.redditScore ?? null}
          detail={
            latestReddit
              ? `${latestReddit.postVolume} posts, ${latestReddit.hotCount} hot`
              : "No data yet"
          }
          sentiment={latestReddit?.sentimentScore ?? null}
        />
        <ScoreCard
          label="News Coverage"
          score={currentScore?.newsScore ?? null}
          detail={
            latestNews
              ? `${latestNews.articleCount} articles this week`
              : "No data yet"
          }
        />
      </div>

      {/* Trend */}
      {sparklineData.length >= 2 && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-8">
          <h2 className="text-text font-semibold text-sm mb-4">
            Health Score Trend
          </h2>
          <Sparkline
            data={sparklineData}
            width={680}
            height={100}
            className="w-full"
          />
          <div className="flex justify-between mt-2 text-text-subtle/60 text-xs mono">
            <span>
              {title.snapshots.length > 0
                ? title.snapshots[title.snapshots.length - 1].weekOf
                    .toISOString()
                    .slice(0, 10)
                : ""}
            </span>
            <span>
              {title.snapshots.length > 0
                ? title.snapshots[0].weekOf.toISOString().slice(0, 10)
                : ""}
            </span>
          </div>
        </div>
      )}

      {/* Player Count History */}
      {playerHistory.length > 1 && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-8">
          <h2 className="text-text font-semibold text-sm mb-4">
            Player Count History
          </h2>
          <div className="overflow-x-auto">
            <div className="flex items-end gap-1 h-24 min-w-[300px]">
              {playerHistory.map((p, i) => {
                const max = Math.max(...playerHistory.map((h) => h.players));
                const height = max > 0 ? (p.players / max) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-accent/40 hover:bg-accent/60 rounded-t transition-colors relative group"
                    style={{ height: `${height}%`, minWidth: "8px" }}
                    title={`${p.date}: ${formatNumber(p.players)} players`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between mt-2 text-text-subtle/60 text-xs mono">
              <span>{playerHistory[0]?.date ?? ""}</span>
              <span>{playerHistory[playerHistory.length - 1]?.date ?? ""}</span>
            </div>
          </div>
        </div>
      )}

      {/* Reddit Top Posts */}
      {topPosts.length > 0 && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-8">
          <h2 className="text-text font-semibold text-sm mb-4">
            Top Reddit Posts This Week
          </h2>
          <div className="space-y-3">
            {topPosts.map((post, i) => (
              <a
                key={i}
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 rounded-md bg-surface hover:bg-surface-high border border-border hover:border-border-hover transition-colors duration-150"
              >
                <p className="text-text text-sm line-clamp-2">
                  {post.title}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-text-subtle text-xs">
                  <span className="mono">{formatNumber(post.score)} pts</span>
                  <span>{post.commentCount} comments</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* News Headlines */}
      {topHeadlines.length > 0 && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-8">
          <h2 className="text-text font-semibold text-sm mb-4">
            Recent News
          </h2>
          <div className="space-y-3">
            {topHeadlines.map((headline, i) => (
              <a
                key={i}
                href={headline.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 rounded-md bg-surface hover:bg-surface-high border border-border hover:border-border-hover transition-colors duration-150"
              >
                <p className="text-text text-sm line-clamp-2">
                  {headline.title}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-text-subtle text-xs">
                  {headline.source && <span>{headline.source}</span>}
                  {headline.date && (
                    <span>
                      {new Date(headline.date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Limited Data Notice */}
      {!hasSteamData && (
        <div className="bg-warning/5 border border-warning/20 rounded-lg p-4 mb-8">
          <p className="text-warning text-sm font-medium">Limited Data</p>
          <p className="text-text-muted text-xs mt-1">
            {title.name} doesn&apos;t have Steam player count data. The health
            score is calculated from Reddit activity (60%) and news coverage
            (40%) only. Comparisons with full-data titles should be weighted
            accordingly.
          </p>
        </div>
      )}
    </div>
  );
}

function ScoreCard({
  label,
  score,
  detail,
  sentiment,
  available = true,
}: {
  label: string;
  score: number | null;
  detail: string;
  sentiment?: number | null;
  available?: boolean;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-subtle text-xs uppercase tracking-widest font-medium">
          {label}
        </span>
        {!available && (
          <span className="text-[10px] text-warning bg-warning/10 px-1.5 py-0.5 rounded">
            N/A
          </span>
        )}
      </div>
      <div className="mono text-xl font-bold text-text">
        {score != null ? score.toFixed(1) : "--"}
      </div>
      <p className="text-text-subtle text-xs mt-1">{detail}</p>
      {sentiment != null && (
        <p
          className={`text-xs mt-1 ${
            sentiment >= 0.05
              ? "text-secondary"
              : sentiment <= -0.05
                ? "text-tertiary"
                : "text-text-subtle"
          }`}
        >
          Sentiment:{" "}
          {sentiment >= 0.05
            ? "Positive"
            : sentiment <= -0.05
              ? "Negative"
              : "Neutral"}{" "}
          ({sentiment.toFixed(2)})
        </p>
      )}
    </div>
  );
}
