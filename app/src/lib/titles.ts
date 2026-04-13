/**
 * Title universe for ShooterDigest.
 * Each entry defines a competitive FPS title tracked by the pipeline.
 * steamAppId = null means no Steam player data (reweight scoring).
 */

export interface TitleConfig {
  name: string;
  slug: string;
  steamAppId: number | null;
  subreddit: string;
  genre: string;
  steamShare: number;
}

export const TITLES: TitleConfig[] = [
  {
    name: "Counter-Strike 2",
    slug: "counter-strike-2",
    steamAppId: 730,
    subreddit: "cs2",
    genre: "Tactical",
    steamShare: 1.0,
  },
  {
    name: "Valorant",
    slug: "valorant",
    steamAppId: null,
    subreddit: "VALORANT",
    genre: "Tactical",
    steamShare: 0,
  },
  {
    name: "Apex Legends",
    slug: "apex-legends",
    steamAppId: 1172470,
    subreddit: "apexlegends",
    genre: "Battle Royale",
    steamShare: 0.25,
  },
  {
    name: "Overwatch 2",
    slug: "overwatch-2",
    steamAppId: 2357570,
    subreddit: "Overwatch",
    genre: "Hero Shooter",
    steamShare: 0.20,
  },
  {
    name: "Rainbow Six Siege",
    slug: "rainbow-six-siege",
    steamAppId: 359550,
    subreddit: "Rainbow6",
    genre: "Tactical",
    steamShare: 0.35,
  },
  {
    name: "Escape from Tarkov",
    slug: "escape-from-tarkov",
    steamAppId: null,
    subreddit: "EscapefromTarkov",
    genre: "Extraction",
    steamShare: 0,
  },
  {
    name: "Hunt: Showdown 1896",
    slug: "hunt-showdown",
    steamAppId: 594650,
    subreddit: "HuntShowdown",
    genre: "Extraction",
    steamShare: 0.7,
  },
  {
    name: "The Finals",
    slug: "the-finals",
    steamAppId: 2073850,
    subreddit: "thefinals",
    genre: "Arena",
    steamShare: 0.50,
  },
  {
    name: "Marvel Rivals",
    slug: "marvel-rivals",
    steamAppId: 2767030,
    subreddit: "marvelrivals",
    genre: "Hero Shooter",
    steamShare: 0.35,
  },
  {
    name: "Deadlock",
    slug: "deadlock",
    steamAppId: 1422450,
    subreddit: "DeadlockTheGame",
    genre: "Hero Shooter",
    steamShare: 1.0,
  },
  {
    name: "PUBG: Battlegrounds",
    slug: "pubg",
    steamAppId: 578080,
    subreddit: "PUBATTLEGROUNDS",
    genre: "Battle Royale",
    steamShare: 0.80,
  },
  {
    name: "Call of Duty",
    slug: "call-of-duty",
    steamAppId: 1938090,
    subreddit: "CallOfDuty",
    genre: "Large-Scale",
    steamShare: 0.15,
  },
];
