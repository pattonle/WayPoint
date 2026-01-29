"""
API operations using aiohttp for the WayPoint Discord bot.
"""
import aiohttp
from datetime import datetime, timedelta
from config import API_ENDPOINTS, PLAYER_BRIDGE_URL


class API:
    """Handles all API operations for fetching Apex Legends data."""
    
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
    
    async def fetch_all_data(self):
        """
        Fetch and update all API data (predator, map, server).
        Implements basic caching to avoid excessive API calls.
        """
        # Check cache
        now = datetime.now()
        if self.last_fetch and (now - self.last_fetch) < self.cache_duration:
            print("⚡ Using cached API data")
            return
        
        responses = {}
        
        async with aiohttp.ClientSession() as session:
            for key, url in API_ENDPOINTS.items():
                try:
                    async with session.get(url) as resp:
                        # Try to parse as JSON regardless of content-type
                        # (some APIs return JSON with text/plain header)
                        try:
                            responses[key] = await resp.json(content_type=None)
                            print(f"✅ Fetched {key} data")
                        except:
                            # If JSON parsing fails, it's truly not JSON
                            text = await resp.text()
                            content_type = resp.headers.get('Content-Type', '')
                            print(f"⚠️ {key} returned non-JSON response (type: {content_type})")
                            print(f"   Response preview: {text[:200]}")
                            responses[key] = {}  # Use empty dict as fallback
                except Exception as e:
                    print(f"❌ Failed to fetch {key} from {url}: {e}")
                    responses[key] = {}  # Ensure key exists even on error
        
        # Parse and store data
        self.map_data = responses.get("map", {})
        self.ltm_data = self.map_data.get('ltm', {})
        self.server_data = responses.get("server", {})
        self.predator_data = responses.get("predator", {})
        self.predcap_data = self.predator_data.get('RP', {})
        self.matchmaking_server_data = self.server_data.get('EA_novafusion', {})
        self.crossplay_server_data = self.server_data.get('ApexOauth_Crossplay', {})
        self.console_server_data = self.server_data.get('otherPlatforms', {})
        
        self.last_fetch = now
        print(f"✅ API data updated at {now.strftime('%I:%M:%S %p')}")
    
    async def fetch_player_stats(self, apex_uid, platform):
        """
        Fetch player statistics from the API.
        
        Args:
            apex_uid (str): Apex Legends UID
            platform (str): Gaming platform (PC, PS4, X1)
            
        Returns:
            dict: Player statistics data
            
        Raises:
            Exception: If API request fails
        """
        url = f"{PLAYER_BRIDGE_URL}&uid={apex_uid}&platform={platform}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                print(f"❌ Failed to fetch player stats for UID {apex_uid}: {e}")
                raise
    
    async def get_apex_uid(self, gamertag, platform):
        """
        Convert a gamertag to Apex UID.
        
        Args:
            gamertag (str): Player's gamertag
            platform (str): Gaming platform (PC, PS4, X1)
            
        Returns:
            str: Apex Legends UID
            
        Raises:
            Exception: If API request fails or UID not found
        """
        url = f"{PLAYER_BRIDGE_URL}&player={gamertag}&platform={platform}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data['global']['uid']
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
        if platform == "PC" and 'PC' in self.predcap_data:
            return self.predcap_data['PC']['val']
        elif platform == "X1" and 'X1' in self.predcap_data:
            return self.predcap_data['X1']['val']
        elif platform == "PS4" and 'PS4' in self.predcap_data:
            return self.predcap_data['PS4']['val']
        return 0
