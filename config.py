"""
Configuration constants and environment variables for the WayPoint Discord bot.
"""
import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord and API credentials
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
APEX_API_KEY = os.getenv('APEX_API_KEY')
STEAM_API_KEY = os.getenv('STEAM_API_KEY')

# API endpoints
API_ENDPOINTS = {
    "predator": f"https://api.mozambiquehe.re/predator?auth={APEX_API_KEY}",
    "map": f"https://api.mozambiquehe.re/maprotation?auth={APEX_API_KEY}&version=2",
    "server": f"https://api.mozambiquehe.re/servers?auth={APEX_API_KEY}&version=2",
    "steam_game": f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={{steam_id}}"
}

# API URL templates
PLAYER_BRIDGE_URL = f"https://api.mozambiquehe.re/bridge?auth={APEX_API_KEY}"

# Discord bot configuration
ADMIN_ROLE = "Admin"

# Timezone configuration
TIMEZONE_ET = ZoneInfo("America/New_York")

# Database configuration
DB_PATH = "server.db"
