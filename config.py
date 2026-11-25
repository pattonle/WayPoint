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

_owner_id_raw = os.getenv('OWNER_DISCORD_ID')
OWNER_DISCORD_ID = int(_owner_id_raw) if _owner_id_raw and _owner_id_raw.isdigit() else None

# Global API endpoints polled periodically
API_ENDPOINTS = {
    "predator": f"https://api.mozambiquehe.re/predator?auth={APEX_API_KEY}",
    "map": f"https://api.mozambiquehe.re/maprotation?auth={APEX_API_KEY}&version=2",
    "server": f"https://api.mozambiquehe.re/servers?auth={APEX_API_KEY}&version=2",
}

# API URL templates
PLAYER_BRIDGE_URL = f"https://api.mozambiquehe.re/bridge?auth={APEX_API_KEY}"
STEAM_PLAYER_SUMMARIES_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_RESOLVE_VANITY_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"

# Ranked RP tier thresholds (ordered highest to lowest, excluding Predator cap)
RANK_THRESHOLDS = [
    (16000, "Master"),
    (12000, "Diamond"),
    (8500, "Platinum"),
    (5500, "Gold"),
    (3000, "Silver"),
    (1000, "Bronze"),
]

# Discord bot configuration
ADMIN_ROLE = "Admin"

# Timezone configuration
TIMEZONE_ET = ZoneInfo("America/New_York")

# Database configuration
DB_PATH = "server.db"
