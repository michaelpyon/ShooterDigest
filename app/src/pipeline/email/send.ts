/**
 * Weekly email digest sender using Resend.
 * Called at the end of a successful pipeline run.
 */

import { PrismaClient } from "@prisma/client";
import { Resend } from "resend";
import { buildDigestHtml } from "./template";

const prisma = new PrismaClient();

export async function sendWeeklyDigest() {
  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey) {
    console.log("[Email] RESEND_API_KEY not set, skipping email delivery.");
    return;
  }

  const resend = new Resend(resendKey);
  const fromAddress = process.env.EMAIL_FROM ?? "digest@shooterdigest.com";
  const siteUrl = process.env.SITE_URL ?? "https://shooter.michaelpyon.com";

  // Get active subscribers
  const subscribers = await prisma.subscriber.findMany({
    where: { status: "active" },
  });

  if (subscribers.length === 0) {
    console.log("[Email] No active subscribers. Skipping.");
    return;
  }

  // Build digest content
  const digestData = await getDigestData();
  const { subject, html } = buildDigestHtml(digestData, siteUrl);

  console.log(
    `[Email] Sending to ${subscribers.length} subscribers. Subject: "${subject}"`
  );

  // Send to each subscriber individually (for unsubscribe link personalization)
  let sent = 0;
  let failed = 0;

  for (const sub of subscribers) {
    try {
      const unsubscribeUrl = `${siteUrl}/api/subscribe?action=unsubscribe&email=${encodeURIComponent(sub.email)}`;

      const personalizedHtml = html.replace(
        "{{UNSUBSCRIBE_URL}}",
        unsubscribeUrl
      );

      await resend.emails.send({
        from: fromAddress,
        to: sub.email,
        subject,
        html: personalizedHtml,
      });

      sent++;
    } catch (err) {
      console.error(`[Email] Failed to send to ${sub.email}:`, err);
      failed++;
    }
  }

  console.log(`[Email] Done. Sent: ${sent}, Failed: ${failed}`);
}

interface DigestTitle {
  name: string;
  slug: string;
  compositeScore: number;
  previousScore: number | null;
  change: number | null;
  hasSteamData: boolean;
}

interface DigestData {
  titles: DigestTitle[];
  topMovers: DigestTitle[];
  biggestDrops: DigestTitle[];
  weekOf: string;
}

async function getDigestData(): Promise<DigestData> {
  const titles = await prisma.title.findMany({
    where: { isActive: true },
    include: {
      scores: {
        orderBy: { date: "desc" },
        take: 2,
      },
    },
  });

  const digestTitles: DigestTitle[] = titles
    .map((t) => {
      const current = t.scores[0];
      const previous = t.scores[1];

      return {
        name: t.name,
        slug: t.slug,
        compositeScore: current?.compositeScore ?? 0,
        previousScore: previous?.compositeScore ?? null,
        change:
          current && previous
            ? current.compositeScore - previous.compositeScore
            : null,
        hasSteamData: t.steamAppId != null,
      };
    })
    .sort((a, b) => b.compositeScore - a.compositeScore);

  const withChanges = digestTitles.filter((t) => t.change != null);
  const topMovers = [...withChanges]
    .sort((a, b) => (b.change ?? 0) - (a.change ?? 0))
    .slice(0, 3);
  const biggestDrops = [...withChanges]
    .sort((a, b) => (a.change ?? 0) - (b.change ?? 0))
    .slice(0, 3);

  const weekOf = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return { titles: digestTitles, topMovers, biggestDrops, weekOf };
}
