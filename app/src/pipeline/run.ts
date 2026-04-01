/**
 * ShooterDigest Pipeline Runner.
 *
 * Runs as a Railway cron job. Collects data from all sources,
 * computes scores, writes to Neon Postgres, then sends the weekly email.
 *
 * Schedule: Mondays 5 AM ET (data pipeline) + 8 AM ET (email delivery).
 * Merged into single job: pipeline runs, then sends email on success.
 */

import { PrismaClient } from "@prisma/client";
import { fetchSteamPlayers } from "./adapters/steam";
import { fetchRedditData } from "./adapters/reddit";
import { fetchGoogleNews } from "./adapters/news";
import { computeScore, type ScoreInput } from "./score";
import { sendWeeklyDigest } from "./email/send";
import { TITLES, type TitleConfig } from "@/lib/titles";

const prisma = new PrismaClient();

async function run() {
  console.log("[Pipeline] Starting ShooterDigest pipeline run...");
  const runStart = new Date();

  // Create pipeline run record
  const pipelineRun = await prisma.pipelineRun.create({
    data: { status: "running" },
  });

  let hadErrors = false;

  try {
    // Ensure all titles exist in DB
    await seedTitles();

    // Fetch all titles from DB
    const titles = await prisma.title.findMany({
      where: { isActive: true },
    });

    for (const title of titles) {
      const config = TITLES.find((t) => t.slug === title.slug);
      if (!config) continue;

      console.log(`[Pipeline] Processing: ${title.name}`);

      // 1. Steam data
      if (config.steamAppId) {
        try {
          const steamData = await fetchSteamPlayers(config.steamAppId);
          if (steamData) {
            await prisma.playerData.create({
              data: {
                titleId: title.id,
                currentPlayers: steamData.currentPlayers,
                peak24h: steamData.peak24h,
                date: steamData.fetchedAt,
              },
            });
            console.log(
              `  Steam: ${steamData.currentPlayers.toLocaleString()} players`
            );
          }
        } catch (err) {
          hadErrors = true;
          await logError("steam", title.id, err);
        }
      }

      // 2. Reddit data
      try {
        const redditData = await fetchRedditData(config.subreddit);
        if (redditData) {
          await prisma.redditData.create({
            data: {
              titleId: title.id,
              postVolume: redditData.postVolume,
              hotCount: redditData.hotCount,
              sentimentScore: redditData.sentimentScore,
              topPostsJson: JSON.stringify(redditData.topPosts),
              date: redditData.fetchedAt,
            },
          });
          console.log(
            `  Reddit: ${redditData.postVolume} posts, sentiment ${redditData.sentimentScore?.toFixed(2) ?? "N/A"}`
          );
        }
      } catch (err) {
        hadErrors = true;
        await logError("reddit", title.id, err);
      }

      // 3. Google News
      try {
        const newsData = await fetchGoogleNews(config.name);
        if (newsData) {
          await prisma.newsData.create({
            data: {
              titleId: title.id,
              articleCount: newsData.articleCount,
              topHeadlinesJson: JSON.stringify(newsData.topHeadlines),
              date: newsData.fetchedAt,
            },
          });
          console.log(`  News: ${newsData.articleCount} articles`);
        }
      } catch (err) {
        hadErrors = true;
        await logError("news", title.id, err);
      }

      // 4. Compute score
      try {
        const scoreInput = await buildScoreInput(title.id, config);
        const scoreOutput = computeScore(scoreInput);

        await prisma.score.create({
          data: {
            titleId: title.id,
            compositeScore: scoreOutput.compositeScore,
            playerScore: scoreOutput.playerScore,
            redditScore: scoreOutput.redditScore,
            newsScore: scoreOutput.newsScore,
          },
        });

        // Write weekly snapshot
        const weekOf = getWeekStart(new Date());
        await prisma.snapshot.upsert({
          where: {
            titleId_weekOf: { titleId: title.id, weekOf },
          },
          update: {
            compositeScore: scoreOutput.compositeScore,
            playerCountAvg: scoreInput.currentPlayers,
            redditVolumeAvg: scoreInput.postVolume,
            newsCountAvg: scoreInput.articleCount,
          },
          create: {
            titleId: title.id,
            weekOf,
            compositeScore: scoreOutput.compositeScore,
            playerCountAvg: scoreInput.currentPlayers,
            redditVolumeAvg: scoreInput.postVolume,
            newsCountAvg: scoreInput.articleCount,
          },
        });

        console.log(`  Score: ${scoreOutput.compositeScore}`);
      } catch (err) {
        hadErrors = true;
        await logError("score", title.id, err);
      }

      // Rate limiting: 1 second between titles to stay under Reddit limits
      await sleep(1000);
    }

    // Update pipeline run status
    await prisma.pipelineRun.update({
      where: { id: pipelineRun.id },
      data: {
        status: hadErrors ? "completed_with_errors" : "complete",
        completedAt: new Date(),
      },
    });

    // Send weekly email digest on success
    if (!hadErrors) {
      console.log("[Pipeline] Sending weekly email digest...");
      await sendWeeklyDigest();
    } else {
      console.log(
        "[Pipeline] Completed with errors. Skipping email delivery."
      );
    }

    const elapsed = (Date.now() - runStart.getTime()) / 1000;
    console.log(`[Pipeline] Done in ${elapsed.toFixed(1)}s`);
  } catch (err) {
    console.error("[Pipeline] Fatal error:", err);
    await prisma.pipelineRun.update({
      where: { id: pipelineRun.id },
      data: {
        status: "failed",
        completedAt: new Date(),
        errorLog: err instanceof Error ? err.message : String(err),
      },
    });
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

/**
 * Build score input by fetching the latest data and historical averages.
 */
async function buildScoreInput(
  titleId: number,
  config: TitleConfig
): Promise<ScoreInput> {
  const hasSteamData = config.steamAppId != null;

  // Get latest player data
  const latestPlayer = await prisma.playerData.findFirst({
    where: { titleId },
    orderBy: { date: "desc" },
  });

  // Get 30-day average player count
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  const playerAvg = await prisma.playerData.aggregate({
    where: { titleId, date: { gte: thirtyDaysAgo } },
    _avg: { currentPlayers: true },
  });

  // Get latest Reddit data
  const latestReddit = await prisma.redditData.findFirst({
    where: { titleId },
    orderBy: { date: "desc" },
  });

  // Get 30-day average Reddit volume
  const redditAvg = await prisma.redditData.aggregate({
    where: { titleId, date: { gte: thirtyDaysAgo } },
    _avg: { postVolume: true },
  });

  // Get latest news data
  const latestNews = await prisma.newsData.findFirst({
    where: { titleId },
    orderBy: { date: "desc" },
  });

  // Get 30-day average news count
  const newsAvg = await prisma.newsData.aggregate({
    where: { titleId, date: { gte: thirtyDaysAgo } },
    _avg: { articleCount: true },
  });

  return {
    hasSteamData,
    currentPlayers: latestPlayer?.currentPlayers ?? null,
    historicalAvgPlayers: playerAvg._avg.currentPlayers ?? null,
    postVolume: latestReddit?.postVolume ?? 0,
    historicalAvgPostVolume: redditAvg._avg.postVolume ?? null,
    sentimentScore: latestReddit?.sentimentScore ?? null,
    hotCount: latestReddit?.hotCount ?? 0,
    articleCount: latestNews?.articleCount ?? 0,
    historicalAvgArticleCount: newsAvg._avg.articleCount ?? null,
  };
}

/**
 * Ensure all titles from the config exist in the database.
 */
async function seedTitles() {
  for (const t of TITLES) {
    await prisma.title.upsert({
      where: { slug: t.slug },
      update: {
        name: t.name,
        steamAppId: t.steamAppId,
        subreddit: t.subreddit,
        genreTags: [t.genre],
        steamShare: t.steamShare,
      },
      create: {
        name: t.name,
        slug: t.slug,
        steamAppId: t.steamAppId,
        subreddit: t.subreddit,
        genreTags: [t.genre],
        steamShare: t.steamShare,
      },
    });
  }
}

async function logError(
  source: string,
  titleId: number | null,
  err: unknown
) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(`  [Error] ${source}: ${message}`);
  try {
    await prisma.pipelineError.create({
      data: {
        source,
        titleId,
        errorMessage: message,
      },
    });
  } catch {
    // Don't fail the pipeline for error logging failures
  }
}

function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Run the pipeline
run().catch(console.error);
