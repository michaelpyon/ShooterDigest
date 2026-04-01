/**
 * Steam Web API adapter.
 * Uses ISteamUserStats/GetNumberOfCurrentPlayers for concurrent player counts.
 * No API key required for this endpoint.
 */

export interface SteamPlayerData {
  currentPlayers: number;
  peak24h: number | null;
  fetchedAt: Date;
}

/**
 * Fetch current concurrent player count from Steam Web API.
 * Returns null on failure (caller should log to pipeline_errors).
 */
export async function fetchSteamPlayers(
  appId: number
): Promise<SteamPlayerData | null> {
  const url = `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=${appId}`;

  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "ShooterDigest/2.0" },
      signal: AbortSignal.timeout(10_000),
    });

    if (!res.ok) {
      console.error(
        `Steam API returned ${res.status} for app ${appId}`
      );
      return null;
    }

    const data = await res.json();
    const count = data?.response?.player_count;

    if (count == null) {
      console.error(`Steam API returned no player_count for app ${appId}`);
      return null;
    }

    return {
      currentPlayers: count,
      // Steam Web API doesn't provide peak_24h directly.
      // We store current as peak and let history build over time.
      peak24h: null,
      fetchedAt: new Date(),
    };
  } catch (err) {
    console.error(`Steam API fetch failed for app ${appId}:`, err);
    return null;
  }
}
