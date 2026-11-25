"""
API operations using aiohttp for the WayPoint Discord bot.
"""
import aiohttp
from datetime import datetime, timedelta
from config import (
    API_ENDPOINTS,
    PLAYER_BRIDGE_URL,
    STEAM_API_KEY,
    STEAM_PLAYER_SUMMARIES_URL,
    STEAM_RESOLVE_VANITY_URL,
)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


class API:
    """Handles all API operations for fetching Apex Legends and Steam data."""

    def __init__(self):
        """Initialize the API instance."""
        self.map_data = {}
        self.ltm_data = {}
        self.server_data = {}
        self.predator_data = {}
        self.predcap_data = {}
        self.matchmaking_server_data = {}
        self.crossplay_server_data = {}
        self.console_server_data = {}
        self.last_fetch = None
        self.cache_duration = timedelta(seconds=30)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return a reusable aiohttp ClientSession with a default timeout."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        return self._session

    async def close(self):
        """Close the underlying aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def fetch_all_data(self):
        """
        Fetch and update all global API data (predator, map, server).
        Implements basic caching to avoid excessive API calls.
        """
        now = datetime.now()
        if self.last_fetch and (now - self.last_fetch) < self.cache_duration:
            print("⚡ Using cached API data")
            return

        responses = {}
        session = await self._get_session()

        for key, url in API_ENDPOINTS.items():
            try:
                async with session.get(url) as resp:
                    try:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict) and "Error" in data:
                            print(f"⚠️ {key} API returned error: {data['Error']}")
                            responses[key] = {}
                        else:
                            responses[key] = data if isinstance(data, dict) else {}
                            print(f"✅ Fetched {key} data")
                    except Exception:
                        text = await resp.text()
                        content_type = resp.headers.get('Content-Type', '')
                        print(f"⚠️ {key} returned non-JSON response (type: {content_type})")
                        print(f"   Response preview: {text[:200]}")
                        responses[key] = {}
            except Exception as e:
                print(f"❌ Failed to fetch {key} from {url}: {e}")
                responses[key] = {}

        # Preserve previous non-empty data if a single fetch failed
        if responses.get("map"):
            self.map_data = responses["map"]
            self.ltm_data = self.map_data.get('ltm', {})
        if responses.get("server"):
            self.server_data = responses["server"]
            self.matchmaking_server_data = self.server_data.get('EA_novafusion', {})
            self.crossplay_server_data = self.server_data.get('ApexOauth_Crossplay', {})
            self.console_server_data = self.server_data.get('otherPlatforms', {})
        if responses.get("predator"):
            self.predator_data = responses["predator"]
            self.predcap_data = self.predator_data.get('RP', {})

        self.last_fetch = now
        print(f"✅ API data updated at {now.strftime('%I:%M:%S %p')}")

    async def _fetch_bridge(self, params: dict) -> dict:
        """Query the Mozambique Here /bridge endpoint and validate the payload."""
        session = await self._get_session()
        async with session.get(PLAYER_BRIDGE_URL, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if isinstance(data, dict) and "Error" in data:
                raise ValueError(data["Error"])
            if not isinstance(data, dict) or "global" not in data:
                raise ValueError("Unexpected response from Apex API.")
            return data

    async def fetch_player_stats(self, apex_uid, platform):
        """
        Fetch player statistics from the API by Apex UID.

        Args:
            apex_uid (str): Apex Legends UID
            platform (str): Gaming platform (PC, PS4, X1)

        Returns:
            dict: Player statistics data
        """
        try:
            return await self._fetch_bridge({"uid": apex_uid, "platform": platform})
        except Exception as e:
            print(f"❌ Failed to fetch player stats for UID {apex_uid}: {e}")
            raise

    async def fetch_player_stats_by_name(self, gamertag, platform):
        """Fetch player statistics directly by gamertag and platform."""
        try:
            return await self._fetch_bridge({"player": gamertag, "platform": platform})
        except Exception as e:
            print(f"❌ Failed to fetch player stats for {gamertag}: {e}")
            raise

    async def get_apex_uid(self, gamertag, platform):
        """
        Convert a gamertag to Apex UID.

        Args:
            gamertag (str): Player's gamertag
            platform (str): Gaming platform (PC, PS4, X1)

        Returns:
            str: Apex Legends UID
        """
        try:
            data = await self._fetch_bridge({"player": gamertag, "platform": platform})
            uid = data['global'].get('uid')
            if not uid:
                raise ValueError(f"UID not found for {gamertag} on {platform}.")
            return str(uid)
        except Exception as e:
            print(f"❌ Failed to get UID for gamertag {gamertag}: {e}")
            raise

    def get_predcap_value(self, platform):
        """
        Get the predator cap value for a specific platform.

        Args:
            platform (str): Gaming platform (PC, PS4, X1)

        Returns:
            int: Predator cap RP value, or 0 if not available
        """
        entry = self.predcap_data.get(platform)
        if isinstance(entry, dict):
            return entry.get('val', 0)
        return 0


async def get_player_game_async(player_id):
    """
    Async helper to get the currently-running gameid for a Steam player.
    Returns the `gameid` (string) or None if not in-game / on error.
    """
    if not STEAM_API_KEY:
        return None
    params = {"key": STEAM_API_KEY, "steamids": player_id}
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        try:
            async with session.get(STEAM_PLAYER_SUMMARIES_URL, params=params) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    text = await resp.text()
                    print(f"⚠️ Non-JSON Steam response: {text[:200]}")
                    return None
                players = data.get('response', {}).get('players', [])
                if not players:
                    return None
                return players[0].get('gameid')
        except Exception as e:
            print(f"❌ Failed to fetch Steam player data for {player_id}: {e}")
            return None


async def resolve_vanity_async(vanity):
    """
    Resolve a Steam vanity URL to a SteamID64 using the Steam Web API.
    Returns the SteamID64 string or None on failure.
    """
    if not STEAM_API_KEY:
        return None
    params = {"key": STEAM_API_KEY, "vanityurl": vanity}
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        try:
            async with session.get(STEAM_RESOLVE_VANITY_URL, params=params) as resp:
                data = await resp.json(content_type=None)
                response = data.get('response', {})
                if response.get('success') == 1:
                    return response.get('steamid')
                return None
        except Exception as e:
            print(f"❌ Failed to resolve vanity URL {vanity}: {e}")
            return None


async def get_steam_player_async(steam_identifier):
    """
    Get Steam player summary for a SteamID64 or vanity name.
    Returns the player dict from GetPlayerSummaries or None.
    """
    if not STEAM_API_KEY:
        return None
    steam_id = steam_identifier
    if not str(steam_identifier).isdigit():
        steam_id = await resolve_vanity_async(steam_identifier)
        if steam_id is None:
            return None

    params = {"key": STEAM_API_KEY, "steamids": steam_id}
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        try:
            async with session.get(STEAM_PLAYER_SUMMARIES_URL, params=params) as resp:
                data = await resp.json(content_type=None)
                players = data.get('response', {}).get('players', [])
                if not players:
                    return None
                return players[0]
        except Exception as e:
            print(f"❌ Failed to fetch Steam player summary for {steam_id}: {e}")
            return None
