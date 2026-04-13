import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

/**
 * GET /api/rss
 * RSS feed endpoint for the weekly ShooterDigest scores.
 */
export async function GET() {
  const siteUrl = process.env.SITE_URL ?? "https://shooter.michaelpyon.com";

  try {
    const titles = await prisma.title.findMany({
      where: { isActive: true },
      include: {
        scores: {
          orderBy: { date: "desc" },
          take: 1,
        },
        snapshots: {
          orderBy: { weekOf: "desc" },
          take: 1,
        },
      },
    });

    // Sort by score descending
    titles.sort(
      (a, b) =>
        (b.scores[0]?.compositeScore ?? 0) -
        (a.scores[0]?.compositeScore ?? 0)
    );

    const latestDate =
      titles[0]?.scores[0]?.date ?? new Date();

    const items = titles.map((t) => {
      const score = t.scores[0];
      const scoreStr = score ? score.compositeScore.toFixed(1) : "N/A";
      const steamBadge = t.steamAppId == null ? " [Limited Data]" : "";

      return `    <item>
      <title>${escapeXml(t.name)}: Health Score ${scoreStr}${steamBadge}</title>
      <link>${siteUrl}/title/${t.slug}</link>
      <guid isPermaLink="false">${t.slug}-${score?.date?.toISOString().slice(0, 10) ?? "unknown"}</guid>
      <pubDate>${(score?.date ?? new Date()).toUTCString()}</pubDate>
      <description>${escapeXml(t.name)} health score is ${scoreStr}/100. Genre: ${t.genreTags[0] ?? "FPS"}.${steamBadge}</description>
    </item>`;
    });

    const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>ShooterDigest: Competitive FPS Market Intelligence</title>
    <link>${siteUrl}</link>
    <description>Weekly competitive FPS market intelligence. Player counts, community sentiment, and news coverage.</description>
    <language>en-us</language>
    <lastBuildDate>${latestDate instanceof Date ? latestDate.toUTCString() : new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${siteUrl}/api/rss" rel="self" type="application/rss+xml"/>
${items.join("\n")}
  </channel>
</rss>`;

    return new NextResponse(rss, {
      headers: {
        "Content-Type": "application/rss+xml; charset=utf-8",
        "Cache-Control": "public, max-age=3600, s-maxage=3600",
      },
    });
  } catch (err) {
    console.error("RSS feed error:", err);
    return new NextResponse("RSS feed unavailable.", { status: 500 });
  }
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
