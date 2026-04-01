import { prisma } from "@/lib/db";
import { TitleCard, type TitleCardData } from "@/components/title-card";
import { SubscribeForm } from "@/components/subscribe-form";

export const revalidate = 3600; // Revalidate every hour

async function getDashboardData(): Promise<TitleCardData[]> {
  const titles = await prisma.title.findMany({
    where: { isActive: true },
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
        take: 1,
      },
      redditData: {
        orderBy: { date: "desc" },
        take: 1,
      },
    },
  });

  const cards: TitleCardData[] = titles.map((t) => {
    const current = t.scores[0];
    const previous = t.scores[1];
    const change =
      current && previous
        ? current.compositeScore - previous.compositeScore
        : null;

    const sparkline = t.snapshots
      .map((s) => s.compositeScore)
      .reverse();

    return {
      rank: 0, // Set after sorting
      name: t.name,
      slug: t.slug,
      genre: t.genreTags[0] ?? "",
      compositeScore: current?.compositeScore ?? 0,
      change,
      currentPlayers: t.playerData[0]?.currentPlayers ?? null,
      hasSteamData: t.steamAppId != null,
      sparklineData: sparkline,
      sentimentScore: t.redditData[0]?.sentimentScore ?? null,
    };
  });

  // Sort by score descending, assign ranks
  cards.sort((a, b) => b.compositeScore - a.compositeScore);
  cards.forEach((c, i) => {
    c.rank = i + 1;
  });

  return cards;
}

async function getLastUpdated(): Promise<string | null> {
  const run = await prisma.pipelineRun.findFirst({
    where: { status: { in: ["complete", "completed_with_errors"] } },
    orderBy: { completedAt: "desc" },
  });
  return run?.completedAt?.toISOString() ?? null;
}

export default async function Dashboard() {
  let cards: TitleCardData[] = [];
  let lastUpdated: string | null = null;

  try {
    [cards, lastUpdated] = await Promise.all([
      getDashboardData(),
      getLastUpdated(),
    ]);
  } catch {
    // DB not connected yet, show empty state
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#e2e8f0] tracking-tight">
          Competitive FPS Intelligence
        </h1>
        <p className="text-[#6b7280] text-sm mt-1">
          Health scores, player trends, and community sentiment across the
          competitive shooter landscape.
        </p>
        {lastUpdated && (
          <p className="text-[#4b5563] text-xs mt-2 mono">
            Last updated:{" "}
            {new Date(lastUpdated).toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
              timeZoneName: "short",
            })}
          </p>
        )}
      </div>

      {/* Column headers */}
      {cards.length > 0 && (
        <div className="flex items-center justify-between px-4 mb-2">
          <span className="text-[#6b7280] text-[10px] uppercase tracking-wider font-medium">
            Title
          </span>
          <div className="flex items-center gap-4">
            <span className="text-[#6b7280] text-[10px] uppercase tracking-wider font-medium w-[72px] text-center">
              Trend
            </span>
            <span className="text-[#6b7280] text-[10px] uppercase tracking-wider font-medium w-16 text-right">
              Score
            </span>
          </div>
        </div>
      )}

      {/* Title cards */}
      <div className="space-y-2">
        {cards.length > 0 ? (
          cards.map((card) => <TitleCard key={card.slug} data={card} />)
        ) : (
          <div className="text-center py-16 border border-[#1f2937] rounded-lg bg-[#111111]">
            <p className="text-[#6b7280] text-sm">
              No data yet. Run the pipeline to populate scores.
            </p>
            <p className="text-[#4b5563] text-xs mt-2 mono">
              npm run pipeline
            </p>
          </div>
        )}
      </div>

      {/* Subscribe form */}
      <SubscribeForm />

      {/* Footer */}
      <footer className="border-t border-[#1f2937] mt-8 pt-6 text-center">
        <p className="text-[#4b5563] text-xs">
          ShooterDigest. Competitive FPS market intelligence.
        </p>
        <p className="text-[#374151] text-xs mt-1">
          Data from Steam Web API, Reddit, and Google News.
        </p>
      </footer>
    </div>
  );
}
