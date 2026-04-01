import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

/**
 * GET /api/titles
 * Returns all active titles with their latest scores and sparkline data.
 */
export async function GET() {
  try {
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
      orderBy: { name: "asc" },
    });

    const result = titles.map((t) => {
      const currentScore = t.scores[0];
      const previousScore = t.scores[1];
      const change =
        currentScore && previousScore
          ? currentScore.compositeScore - previousScore.compositeScore
          : null;

      const sparkline = t.snapshots
        .map((s) => s.compositeScore)
        .reverse();

      return {
        id: t.id,
        name: t.name,
        slug: t.slug,
        genre: t.genreTags[0] ?? "",
        hasSteamData: t.steamAppId != null,
        compositeScore: currentScore?.compositeScore ?? 0,
        playerScore: currentScore?.playerScore ?? null,
        redditScore: currentScore?.redditScore ?? null,
        newsScore: currentScore?.newsScore ?? null,
        change,
        currentPlayers: t.playerData[0]?.currentPlayers ?? null,
        sentimentScore: t.redditData[0]?.sentimentScore ?? null,
        sparklineData: sparkline,
      };
    });

    // Sort by composite score descending
    result.sort((a, b) => b.compositeScore - a.compositeScore);

    return NextResponse.json(result);
  } catch (err) {
    console.error("GET /api/titles error:", err);
    return NextResponse.json(
      { error: "Failed to load titles." },
      { status: 500 }
    );
  }
}
