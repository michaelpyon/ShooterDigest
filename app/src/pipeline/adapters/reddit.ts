/**
 * Reddit API adapter with OAuth.
 * Fetches subreddit top posts, computes sentiment via VADER.
 */

import vader from "vader-sentiment";

export interface RedditPost {
  title: string;
  url: string;
  score: number;
  commentCount: number;
  date: string;
}

export interface RedditResult {
  postVolume: number;
  hotCount: number;
  sentimentScore: number | null;
  topPosts: RedditPost[];
  fetchedAt: Date;
}

let cachedToken: { token: string; expiresAt: number } | null = null;

/**
 * Get a Reddit OAuth access token using client credentials.
 */
async function getRedditToken(): Promise<string> {
  const now = Date.now();
  if (cachedToken && cachedToken.expiresAt > now + 60_000) {
    return cachedToken.token;
  }

  const clientId = process.env.REDDIT_CLIENT_ID;
  const clientSecret = process.env.REDDIT_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are required");
  }

  const auth = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");

  const res = await fetch("https://www.reddit.com/api/v1/access_token", {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "ShooterDigest/2.0",
    },
    body: "grant_type=client_credentials",
    signal: AbortSignal.timeout(10_000),
  });

  if (!res.ok) {
    throw new Error(`Reddit OAuth failed: ${res.status}`);
  }

  const data = await res.json();
  cachedToken = {
    token: data.access_token,
    expiresAt: now + data.expires_in * 1000,
  };

  return cachedToken.token;
}

/**
 * Fetch subreddit data: top posts (week), hot posts count, and VADER sentiment.
 */
export async function fetchRedditData(
  subreddit: string
): Promise<RedditResult | null> {
  try {
    const token = await getRedditToken();
    const headers = {
      Authorization: `Bearer ${token}`,
      "User-Agent": "ShooterDigest/2.0",
    };

    // Fetch top posts (weekly)
    const topRes = await fetch(
      `https://oauth.reddit.com/r/${subreddit}/top?t=week&limit=25`,
      { headers, signal: AbortSignal.timeout(10_000) }
    );

    if (!topRes.ok) {
      console.error(`Reddit top posts ${topRes.status} for r/${subreddit}`);
      return null;
    }

    const topData = await topRes.json();
    const posts = topData?.data?.children ?? [];

    // Fetch hot posts for hot count
    const hotRes = await fetch(
      `https://oauth.reddit.com/r/${subreddit}/hot?limit=25`,
      { headers, signal: AbortSignal.timeout(10_000) }
    );

    const hotData = hotRes.ok ? await hotRes.json() : null;
    const hotPosts = hotData?.data?.children ?? [];

    // Compute sentiment from top post titles
    const titles = posts.map(
      (p: { data: { title: string } }) => p.data.title
    );
    let sentimentScore: number | null = null;

    if (titles.length > 0) {
      const scores = titles.map((t: string) => {
        const result = vader.SentimentIntensityAnalyzer.polarity_scores(t);
        return result.compound;
      });
      sentimentScore =
        scores.reduce((a: number, b: number) => a + b, 0) / scores.length;
    }

    // Extract top 3 posts by score
    const topPosts: RedditPost[] = posts
      .sort(
        (a: { data: { score: number } }, b: { data: { score: number } }) =>
          b.data.score - a.data.score
      )
      .slice(0, 3)
      .map(
        (p: {
          data: {
            title: string;
            permalink: string;
            score: number;
            num_comments: number;
            created_utc: number;
          };
        }) => ({
          title: p.data.title,
          url: `https://reddit.com${p.data.permalink}`,
          score: p.data.score,
          commentCount: p.data.num_comments,
          date: new Date(p.data.created_utc * 1000).toISOString(),
        })
      );

    return {
      postVolume: posts.length,
      hotCount: hotPosts.length,
      sentimentScore,
      topPosts,
      fetchedAt: new Date(),
    };
  } catch (err) {
    console.error(`Reddit fetch failed for r/${subreddit}:`, err);
    return null;
  }
}
