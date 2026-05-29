import type { TitleCardData } from "@/components/title-card";

/**
 * Static sample digest used as a fallback when the live database has no data.
 * Numbers are representative of a typical week in the competitive shooter
 * landscape and let visitors see a populated briefing instead of an empty
 * "run the pipeline" state. Replaced automatically once the pipeline writes
 * real scores to the database.
 */

export const SAMPLE_LAST_UPDATED = "2026-05-26T13:00:00.000Z";

interface SampleHeadline {
  title: string;
  url: string;
  source: string;
  date: string;
}

interface SampleRedditPost {
  title: string;
  url: string;
  score: number;
  commentCount: number;
}

export interface SampleTitle {
  name: string;
  slug: string;
  genre: string;
  compositeScore: number;
  change: number | null;
  currentPlayers: number | null;
  hasSteamData: boolean;
  sparklineData: number[];
  sentimentScore: number | null;
  launchedLabel: string;
  playerScore: number | null;
  redditScore: number | null;
  newsScore: number | null;
  postVolume: number;
  hotCount: number;
  articleCount: number;
  playerHistory: number[];
  summary: string;
  topPosts: SampleRedditPost[];
  topHeadlines: SampleHeadline[];
}

export const SAMPLE_TITLES: SampleTitle[] = [
  {
    name: "Counter-Strike 2",
    slug: "counter-strike-2",
    genre: "Tactical FPS",
    compositeScore: 92.4,
    change: 1.8,
    currentPlayers: 1142380,
    hasSteamData: true,
    sparklineData: [84, 85, 83, 86, 88, 87, 89, 90, 88, 91, 90, 92],
    sentimentScore: 0.21,
    launchedLabel: "Sep 2023",
    playerScore: 96.0,
    redditScore: 88.5,
    newsScore: 90.0,
    postVolume: 1840,
    hotCount: 62,
    articleCount: 34,
    playerHistory: [
      980000, 1010000, 995000, 1040000, 1075000, 1060000, 1098000, 1120000,
      1090000, 1135000, 1118000, 1142380,
    ],
    summary:
      "Counter-Strike 2 held the top spot again as the spring operation drove a steady climb in concurrent players. The new anti-cheat pass landed well with the community and Premier matchmaking queues stayed healthy through the week.",
    topPosts: [
      {
        title: "The new VAC update actually banned a cheater in my last match",
        url: "https://reddit.com/r/GlobalOffensive",
        score: 18420,
        commentCount: 1240,
      },
      {
        title: "Spring operation missions ranked from best to worst",
        url: "https://reddit.com/r/GlobalOffensive",
        score: 9310,
        commentCount: 612,
      },
      {
        title: "Inferno banana smoke lineup that still works after the patch",
        url: "https://reddit.com/r/GlobalOffensive",
        score: 7180,
        commentCount: 288,
      },
    ],
    topHeadlines: [
      {
        title: "Counter-Strike 2 spring operation adds new missions and skins",
        url: "https://example.com/cs2-operation",
        source: "Dexerto",
        date: "2026-05-22",
      },
      {
        title: "Valve ships major anti-cheat update for Counter-Strike 2",
        url: "https://example.com/cs2-anticheat",
        source: "PC Gamer",
        date: "2026-05-20",
      },
    ],
  },
  {
    name: "Valorant",
    slug: "valorant",
    genre: "Tactical FPS",
    compositeScore: 89.7,
    change: 2.3,
    currentPlayers: null,
    hasSteamData: false,
    sparklineData: [80, 82, 81, 83, 85, 84, 86, 87, 85, 88, 87, 90],
    sentimentScore: 0.16,
    launchedLabel: "Jun 2020",
    playerScore: null,
    redditScore: 91.0,
    newsScore: 88.0,
    postVolume: 2210,
    hotCount: 74,
    articleCount: 41,
    playerHistory: [],
    summary:
      "Valorant momentum surged around the new act launch and the reveal of a fresh duelist. Masters viewership numbers carried the conversation, and community sentiment trended positive despite the usual rank reset complaints.",
    topPosts: [
      {
        title: "New duelist abilities breakdown, this kit looks strong",
        url: "https://reddit.com/r/VALORANT",
        score: 21030,
        commentCount: 1860,
      },
      {
        title: "Episode act rank reset hit harder than expected this time",
        url: "https://reddit.com/r/VALORANT",
        score: 8740,
        commentCount: 940,
      },
    ],
    topHeadlines: [
      {
        title: "Valorant reveals new duelist agent ahead of Masters",
        url: "https://example.com/valorant-agent",
        source: "Dot Esports",
        date: "2026-05-24",
      },
      {
        title: "Valorant Masters breaks concurrent viewer record",
        url: "https://example.com/valorant-masters",
        source: "The Esports Observer",
        date: "2026-05-21",
      },
    ],
  },
  {
    name: "Marvel Rivals",
    slug: "marvel-rivals",
    genre: "Hero Shooter",
    compositeScore: 84.1,
    change: 4.6,
    currentPlayers: 487210,
    hasSteamData: true,
    sparklineData: [62, 65, 68, 70, 72, 74, 76, 78, 79, 81, 82, 84],
    sentimentScore: 0.27,
    launchedLabel: "Dec 2024",
    playerScore: 82.0,
    redditScore: 87.0,
    newsScore: 83.0,
    postVolume: 1520,
    hotCount: 58,
    articleCount: 29,
    playerHistory: [
      301000, 322000, 348000, 366000, 389000, 401000, 418000, 437000, 449000,
      462000, 471000, 487210,
    ],
    summary:
      "Marvel Rivals posted the biggest week-over-week gain in the set. A new season with 2 added heroes and a reworked competitive ladder pulled lapsed players back, and sentiment stayed strongly positive across the subreddit.",
    topPosts: [
      {
        title: "Season 4 hero reveal trailer is genuinely incredible",
        url: "https://reddit.com/r/marvelrivals",
        score: 24600,
        commentCount: 2110,
      },
      {
        title: "Ranked rework finally fixed the duo queue problem",
        url: "https://reddit.com/r/marvelrivals",
        score: 11240,
        commentCount: 770,
      },
    ],
    topHeadlines: [
      {
        title: "Marvel Rivals season 4 adds 2 new heroes and a map",
        url: "https://example.com/rivals-season4",
        source: "IGN",
        date: "2026-05-23",
      },
      {
        title: "Marvel Rivals tops 40 million registered players",
        url: "https://example.com/rivals-milestone",
        source: "GamesRadar",
        date: "2026-05-19",
      },
    ],
  },
  {
    name: "Apex Legends",
    slug: "apex-legends",
    genre: "Battle Royale",
    compositeScore: 71.8,
    change: -3.2,
    currentPlayers: 198540,
    hasSteamData: true,
    sparklineData: [82, 81, 80, 78, 79, 77, 76, 75, 74, 73, 73, 72],
    sentimentScore: -0.11,
    launchedLabel: "Feb 2019",
    playerScore: 70.0,
    redditScore: 68.0,
    newsScore: 78.0,
    postVolume: 1130,
    hotCount: 44,
    articleCount: 22,
    playerHistory: [
      258000, 249000, 241000, 233000, 228000, 221000, 216000, 210000, 207000,
      203000, 201000, 198540,
    ],
    summary:
      "Apex Legends slipped again as the player base voiced frustration over the battle pass changes and matchmaking. The new legend reveal drew interest, but sentiment stayed negative and concurrent counts kept drifting down.",
    topPosts: [
      {
        title: "The battle pass changes are the final straw for a lot of us",
        url: "https://reddit.com/r/apexlegends",
        score: 31200,
        commentCount: 4380,
      },
      {
        title: "New legend kit looks fun but matchmaking is still rough",
        url: "https://reddit.com/r/apexlegends",
        score: 6420,
        commentCount: 530,
      },
    ],
    topHeadlines: [
      {
        title: "Apex Legends reveals new legend for upcoming season",
        url: "https://example.com/apex-legend",
        source: "Eurogamer",
        date: "2026-05-22",
      },
      {
        title: "Respawn responds to backlash over Apex battle pass",
        url: "https://example.com/apex-battlepass",
        source: "Kotaku",
        date: "2026-05-20",
      },
    ],
  },
  {
    name: "The Finals",
    slug: "the-finals",
    genre: "Arena FPS",
    compositeScore: 68.5,
    change: 1.1,
    currentPlayers: 64820,
    hasSteamData: true,
    sparklineData: [60, 61, 63, 62, 64, 65, 64, 66, 67, 66, 68, 68],
    sentimentScore: 0.09,
    launchedLabel: "Dec 2023",
    playerScore: 64.0,
    redditScore: 72.0,
    newsScore: 70.0,
    postVolume: 760,
    hotCount: 31,
    articleCount: 16,
    playerHistory: [
      52000, 54000, 57000, 55000, 59000, 61000, 60000, 62000, 63000, 62000,
      64000, 64820,
    ],
    summary:
      "The Finals kept a loyal core engaged with a new map and a fresh ranked split. Destructible arena highlights dominated the clips, and the steady sentiment suggests the player base is settling into a sustainable rhythm.",
    topPosts: [
      {
        title: "New map is the best destructible arena yet, hands down",
        url: "https://reddit.com/r/thefinals",
        score: 8920,
        commentCount: 410,
      },
      {
        title: "Ranked split rewards are actually worth grinding this season",
        url: "https://reddit.com/r/thefinals",
        score: 4150,
        commentCount: 220,
      },
    ],
    topHeadlines: [
      {
        title: "The Finals adds new destructible map in latest update",
        url: "https://example.com/finals-map",
        source: "PCGamesN",
        date: "2026-05-23",
      },
      {
        title: "Embark teases competitive overhaul for The Finals",
        url: "https://example.com/finals-comp",
        source: "VG247",
        date: "2026-05-18",
      },
    ],
  },
  {
    name: "Overwatch 2",
    slug: "overwatch-2",
    genre: "Hero Shooter",
    compositeScore: 65.2,
    change: -1.4,
    currentPlayers: null,
    hasSteamData: false,
    sparklineData: [70, 69, 68, 67, 68, 66, 67, 66, 65, 66, 65, 65],
    sentimentScore: -0.04,
    launchedLabel: "Oct 2022",
    playerScore: null,
    redditScore: 63.0,
    newsScore: 70.0,
    postVolume: 980,
    hotCount: 37,
    articleCount: 19,
    playerHistory: [],
    summary:
      "Overwatch 2 held roughly steady on the strength of a midseason balance patch. The community remains split on the perk system, so sentiment landed near neutral while news coverage stayed solid around the new hero teaser.",
    topPosts: [
      {
        title: "Midseason balance patch notes are a step in the right direction",
        url: "https://reddit.com/r/Overwatch",
        score: 7640,
        commentCount: 690,
      },
      {
        title: "The perk system is growing on me, change my mind",
        url: "https://reddit.com/r/Overwatch",
        score: 5120,
        commentCount: 880,
      },
    ],
    topHeadlines: [
      {
        title: "Overwatch 2 midseason patch reworks two tank heroes",
        url: "https://example.com/ow2-patch",
        source: "Polygon",
        date: "2026-05-21",
      },
      {
        title: "Blizzard teases next Overwatch 2 hero for summer season",
        url: "https://example.com/ow2-hero",
        source: "GameSpot",
        date: "2026-05-17",
      },
    ],
  },
];

export function getSampleCards(): TitleCardData[] {
  const cards: TitleCardData[] = SAMPLE_TITLES.map((t) => ({
    rank: 0,
    name: t.name,
    slug: t.slug,
    genre: t.genre,
    compositeScore: t.compositeScore,
    change: t.change,
    currentPlayers: t.currentPlayers,
    hasSteamData: t.hasSteamData,
    sparklineData: t.sparklineData,
    sentimentScore: t.sentimentScore,
  }));

  cards.sort((a, b) => b.compositeScore - a.compositeScore);
  cards.forEach((c, i) => {
    c.rank = i + 1;
  });

  return cards;
}

export function getSampleTitle(slug: string): SampleTitle | undefined {
  return SAMPLE_TITLES.find((t) => t.slug === slug);
}
