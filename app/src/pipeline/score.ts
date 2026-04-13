/**
 * Score computation engine.
 *
 * Title health score (0-100): weighted composite.
 * - Steam titles: Player Count 50%, Reddit 30%, News 20%
 * - Non-Steam titles: Reddit 60%, News 40% (with "Limited Data" flag)
 *
 * Each sub-score is normalized to 0-100 based on the signal strength
 * relative to the title's own historical baseline.
 */

import { clamp } from "@/lib/utils";

export interface ScoreInput {
  hasSteamData: boolean;

  // Player data (null for non-Steam titles)
  currentPlayers: number | null;
  historicalAvgPlayers: number | null;

  // Reddit data
  postVolume: number;
  historicalAvgPostVolume: number | null;
  sentimentScore: number | null; // -1.0 to +1.0
  hotCount: number;

  // News data
  articleCount: number;
  historicalAvgArticleCount: number | null;
}

export interface ScoreOutput {
  compositeScore: number;
  playerScore: number | null;
  redditScore: number | null;
  newsScore: number | null;
}

/**
 * Compute a title's health score from raw signals.
 */
export function computeScore(input: ScoreInput): ScoreOutput {
  const playerScore = input.hasSteamData
    ? computePlayerScore(input)
    : null;
  const redditScore = computeRedditScore(input);
  const newsScore = computeNewsScore(input);

  let compositeScore: number;

  if (input.hasSteamData && playerScore != null) {
    // Full data: 50% player, 30% reddit, 20% news
    compositeScore =
      playerScore * 0.5 +
      (redditScore ?? 50) * 0.3 +
      (newsScore ?? 50) * 0.2;
  } else {
    // Non-Steam / limited data: 60% reddit, 40% news
    compositeScore =
      (redditScore ?? 50) * 0.6 + (newsScore ?? 50) * 0.4;
  }

  return {
    compositeScore: clamp(Math.round(compositeScore * 10) / 10, 0, 100),
    playerScore: playerScore != null ? clamp(Math.round(playerScore * 10) / 10, 0, 100) : null,
    redditScore: redditScore != null ? clamp(Math.round(redditScore * 10) / 10, 0, 100) : null,
    newsScore: newsScore != null ? clamp(Math.round(newsScore * 10) / 10, 0, 100) : null,
  };
}

/**
 * Player score: current vs. 30-day average.
 * 50 = at average. Higher = above average. Lower = declining.
 */
function computePlayerScore(input: ScoreInput): number | null {
  if (input.currentPlayers == null) return null;
  if (input.historicalAvgPlayers == null || input.historicalAvgPlayers === 0) {
    // No history yet, return a neutral score
    return 50;
  }

  const ratio = input.currentPlayers / input.historicalAvgPlayers;
  // Map ratio to 0-100 scale:
  // ratio 0.5 -> 25, ratio 1.0 -> 50, ratio 1.5 -> 75, ratio 2.0 -> 100
  const score = ratio * 50;
  return clamp(score, 0, 100);
}

/**
 * Reddit score: post volume trend + sentiment boost.
 * Volume above average pushes score up. Positive sentiment adds a bonus.
 */
function computeRedditScore(input: ScoreInput): number | null {
  if (input.postVolume === 0 && input.hotCount === 0) return null;

  let volumeScore = 50;
  if (
    input.historicalAvgPostVolume != null &&
    input.historicalAvgPostVolume > 0
  ) {
    const ratio = input.postVolume / input.historicalAvgPostVolume;
    volumeScore = ratio * 50;
  } else if (input.postVolume > 0) {
    // No history. Score based on absolute volume thresholds.
    volumeScore = clamp(input.postVolume * 3, 20, 80);
  }

  // Sentiment bonus: compound score ranges from -1 to +1.
  // Map to -15 to +15 bonus.
  let sentimentBonus = 0;
  if (input.sentimentScore != null) {
    sentimentBonus = input.sentimentScore * 15;
  }

  return clamp(volumeScore + sentimentBonus, 0, 100);
}

/**
 * News score: article count relative to historical average.
 * More coverage = higher score. Normalized 0-100.
 */
function computeNewsScore(input: ScoreInput): number | null {
  if (input.articleCount === 0) return 30; // Some baseline even with no news

  if (
    input.historicalAvgArticleCount != null &&
    input.historicalAvgArticleCount > 0
  ) {
    const ratio = input.articleCount / input.historicalAvgArticleCount;
    return clamp(ratio * 50, 0, 100);
  }

  // No history. Score based on absolute count.
  return clamp(30 + input.articleCount * 8, 0, 100);
}
