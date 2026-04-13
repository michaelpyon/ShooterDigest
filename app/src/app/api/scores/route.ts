import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

/**
 * GET /api/scores?slugs=cs2,valorant&days=90
 * Returns score history for the given title slugs over the specified period.
 * Used by the /compare page.
 */
export async function GET(request: NextRequest) {
  const slugsParam = request.nextUrl.searchParams.get("slugs");
  const daysParam = request.nextUrl.searchParams.get("days");

  if (!slugsParam) {
    return NextResponse.json(
      { error: "slugs parameter required." },
      { status: 400 }
    );
  }

  const slugs = slugsParam.split(",").map((s) => s.trim());
  const days = parseInt(daysParam ?? "90", 10);
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

  try {
    const titles = await prisma.title.findMany({
      where: { slug: { in: slugs }, isActive: true },
      include: {
        snapshots: {
          where: { weekOf: { gte: since } },
          orderBy: { weekOf: "asc" },
        },
      },
    });

    const result = titles.map((t) => ({
      name: t.name,
      slug: t.slug,
      hasSteamData: t.steamAppId != null,
      data: t.snapshots.map((s) => ({
        weekOf: s.weekOf.toISOString(),
        compositeScore: s.compositeScore,
        playerCountAvg: s.playerCountAvg,
        redditVolumeAvg: s.redditVolumeAvg,
        newsCountAvg: s.newsCountAvg,
      })),
    }));

    return NextResponse.json(result);
  } catch (err) {
    console.error("GET /api/scores error:", err);
    return NextResponse.json(
      { error: "Failed to load scores." },
      { status: 500 }
    );
  }
}
