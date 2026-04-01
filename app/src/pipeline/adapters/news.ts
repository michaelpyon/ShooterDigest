/**
 * Google News RSS adapter.
 * Fetches recent news articles about a game title.
 * Free, no API key required.
 */

export interface NewsHeadline {
  title: string;
  url: string;
  source: string;
  date: string;
}

export interface NewsResult {
  articleCount: number;
  topHeadlines: NewsHeadline[];
  fetchedAt: Date;
}

/**
 * Fetch news articles from Google News RSS for a given game name.
 */
export async function fetchGoogleNews(
  gameName: string
): Promise<NewsResult | null> {
  // Handle ambiguous names
  const AMBIGUOUS: Record<string, string> = {
    "The Finals": "The Finals Embark game",
    "Deadlock": "Deadlock Valve game",
    "Call of Duty": "Call of Duty game",
  };

  const searchTerm = AMBIGUOUS[gameName] ?? `${gameName} game`;
  const query = encodeURIComponent(searchTerm);
  const url = `https://news.google.com/rss/search?q=${query}&hl=en-US&gl=US&ceid=US:en`;

  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "ShooterDigest/2.0" },
      signal: AbortSignal.timeout(10_000),
    });

    if (!res.ok) {
      console.error(`Google News RSS returned ${res.status} for "${gameName}"`);
      return null;
    }

    const xml = await res.text();
    const headlines = parseRssItems(xml, gameName);

    return {
      articleCount: headlines.length,
      topHeadlines: headlines.slice(0, 3),
      fetchedAt: new Date(),
    };
  } catch (err) {
    console.error(`Google News fetch failed for "${gameName}":`, err);
    return null;
  }
}

/**
 * Parse RSS XML and extract relevant items.
 * Basic XML parsing without heavy dependencies.
 */
function parseRssItems(xml: string, gameName: string): NewsHeadline[] {
  const items: NewsHeadline[] = [];

  // Simple regex-based XML parsing for RSS items
  const itemRegex = /<item>([\s\S]*?)<\/item>/g;
  let match;

  const nameTokens = gameName
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => !["the", "of", "and", "a", "an"].includes(t))
    .map((t) => t.replace(/[^\w]/g, ""))
    .filter(Boolean);

  while ((match = itemRegex.exec(xml)) !== null) {
    const itemXml = match[1];

    const title = extractTag(itemXml, "title");
    const link = extractTag(itemXml, "link");
    const source = extractTag(itemXml, "source");
    const pubDate = extractTag(itemXml, "pubDate");

    if (!title) continue;

    // Relevance filter: title must contain the game name or all tokens
    const titleLower = title.toLowerCase();
    const fullMatch = gameName.toLowerCase();
    const hasFullName = titleLower.includes(fullMatch);
    const hasAllTokens =
      nameTokens.length > 0 && nameTokens.every((t) => titleLower.includes(t));

    if (!hasFullName && !hasAllTokens) continue;

    // Filter non-gaming articles
    const nonGaming =
      /\b(olympic|nba|nfl|nhl|mlb|soccer|football|basketball|tennis|swimming|medal|playoff|super bowl|world cup)\b/i;
    if (nonGaming.test(title)) continue;

    items.push({
      title: decodeHtmlEntities(title),
      url: link || "",
      source: source || "",
      date: pubDate || "",
    });

    if (items.length >= 10) break;
  }

  return items;
}

function extractTag(xml: string, tag: string): string {
  // Handle CDATA
  const cdataRegex = new RegExp(
    `<${tag}[^>]*>\\s*<!\\[CDATA\\[([\\s\\S]*?)\\]\\]>\\s*</${tag}>`,
    "i"
  );
  const cdataMatch = cdataRegex.exec(xml);
  if (cdataMatch) return cdataMatch[1].trim();

  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i");
  const match = regex.exec(xml);
  if (match) return match[1].trim();

  // For self-closing link tags, get content after the tag
  if (tag === "link") {
    const linkRegex = /<link[^>]*\/?\s*>\s*([^\s<]+)/i;
    const linkMatch = linkRegex.exec(xml);
    if (linkMatch) return linkMatch[1].trim();
  }

  return "";
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .replace(/&apos;/g, "'");
}
