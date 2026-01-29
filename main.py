"""
WayPoint Discord Bot - Main Entry Point
A modular Discord bot for tracking Apex Legends statistics and server status.
"""
import discord
from discord.ext import commands
import logging

from config import DISCORD_TOKEN
from database import Database
from api import API
from commands import setup_all_commands
from tasks import setup_tasks


# Set up logging
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)
discord_logger.addHandler(handler)

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database and API instances
db = Database()
api = API()


@bot.event
async def on_ready():
    """Bot initialization sequence when ready."""
    print("🤖 Bot is starting up...")
    
    # Initialize database
    await db.init()
    
    # Fetch initial API data
    print("⏳ Fetching initial API data...")
    await api.fetch_all_data()
    print("✅ API data loaded successfully!")
    print(f"  - Matchmaking servers: {len(api.matchmaking_server_data)} regions")
    print(f"  - Crossplay servers: {len(api.crossplay_server_data)} regions")
    print(f"  - Console servers: {len(api.console_server_data)} platforms")
    
    # Set up commands
    await setup_all_commands(bot, db, api)
    
    # Sync commands with Discord (must be done AFTER registering commands)
    await bot.tree.sync()
    print("✅ Commands synced with Discord")
    
    # Start periodic tasks
    setup_tasks(bot, db, api)
    
    print(f'✅ {bot.user.name} is online and connected to Discord!')


@bot.event
async def on_guild_join(guild):
    """Automatically save new server config when bot joins a server."""
    await db.save_server_config(discord_server_id=guild.id)
    print(f"✅ Joined new server: {guild.name} ({guild.id}) and added to database.")


# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)


# THINGS TO CONSIDER FOR FUTURE UPDATES

# Priority 1
# - implement error handling for api requests
# - add steam api usage for automatic rp tracking on pc platform
# - fix db so that stats uses discord server uid and users uid to allow same user in different servers
# - implement leaderboard command to view top 3 players in server by rp 

# Priority 2
# - implement nuke command to clear db for admin users
# - implement unregister command to delete user from db
# - implement command to view current registered info
# - implement command to view current tracked rp and time registered
# - implement command to change apex uid or platform
# - implement command to track certain players rp gains (message they're gains/losses)
# - implement command to view current map rotation and server status without player stats