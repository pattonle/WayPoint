import discord 
from discord.ext import commands
from discord import app_commands
import logging 
from dotenv import load_dotenv
import os
import requests
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
import atexit
import aiosqlite

#load environment variables
load_dotenv()
DiscordTOKEN = os.getenv('DISCORD_TOKEN')
ApexAPIKey = os.getenv('APEX_API_KEY')

# Define NEEDED user roles
admin = "Admin"

# Set up logging to a file
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Set a specific format for log messages
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configure the logger for discord.py
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)
discord_logger.addHandler(handler)

et = timezone(timedelta(hours=-5))  

#helper function to format time differences
def format_time_difference(start_time, end_time):
    """Format time difference in a human-readable way"""
    diff = end_time - start_time
    
    days = diff.days
    total_seconds = int(diff.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    else:
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"

# Automatically save new server config when bot joins a server
@bot.event
async def on_guild_join(guild):
    save_server_config(db,
        discord_server_id=guild.id,
        apex_server_channel_id=None
    )
    print(f"✅ Joined new server: {guild.name} ({guild.id}) and added to database.")
db = None

# Initialize the database
def init_db():
    global db
    db = sqlite3.connect('server.db')
    c = db.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            discord_server_id INTEGER PRIMARY KEY,     -- Each Discord server has   unique ID (like social security number)
            apex_server_channel_id INTEGER,        -- Store channel ID for apex server status
            apex_server_message_id INTEGER          -- Store message ID for apex server status
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            discord_id INTEGER PRIMARY KEY, -- Each Discord user has unique ID
            discord_server_id INTEGER,              -- Foreign key to link user to a server
            apex_uid TEXT,                 -- Store Apex Legends UID
            platform TEXT,         -- Store platform for Apex Legends
            current_RP INTEGER,              -- Store current RP of the user
            time_registered TIMESTAMP,  -- Timestamp of registration
            stats_message_id INTEGER,      -- Message ID for stats embed
            stats_channel_id INTEGER       -- Channel ID for stats embed
        )
    ''')
    db.commit()
    # Migration: ensure required columns exist (add missing columns safely)
    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    if 'platform' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN platform TEXT")
        print("⚙️ Migrated: added 'platform' column to users table")
    if 'current_RP' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN current_RP INTEGER")
        print("⚙️ Migrated: added 'current_RP' column to users table")
    if 'stats_message_id' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN stats_message_id INTEGER")
        print("⚙️ Migrated: added 'stats_message_id' column to users table")
    if 'stats_channel_id' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN stats_channel_id INTEGER")
        print("⚙️ Migrated: added 'stats_channel_id' column to users table")
    db.commit()
    print("✅ Database created and ready!")
    return db
db = init_db()
atexit.register(lambda: db.close())
# save or update server config
async def save_server_config(db, discord_server_id, apex_server_channel_id=None, apex_server_message_id=None):
    """Insert or update server config. Only overwrite columns when a non-None value is provided.

    Usage:
    save_server_config(db, discord_server_id, apex_server_channel_id=123, apex_server_message_id=456)
    will update only the provided columns for that server and preserve other fields.
    """
    async with db.execute('SELECT * FROM servers WHERE discord_server_id = ?', (discord_server_id,)) as cursor:
        row = await cursor.fetchone()

    if row is None:
        # No existing row — insert whatever values were provided (others will be NULL)
        await db.execute('''
            INSERT INTO servers (discord_server_id, apex_server_channel_id, apex_server_message_id)
            VALUES (?, ?, ?)
        ''', (discord_server_id, apex_server_channel_id, apex_server_message_id))
    else:
        # Update only the provided columns
        if apex_server_channel_id is not None:
            await db.execute('''
                UPDATE servers
                SET apex_server_channel_id = ?
                WHERE discord_server_id = ?
            ''', (apex_server_channel_id, discord_server_id))

        if apex_server_message_id is not None:
            await db.execute('''
                UPDATE servers
                SET apex_server_message_id = ?
                WHERE discord_server_id = ?
            ''', (apex_server_message_id, discord_server_id))

    await db.commit()
    print(f"✅ Server {discord_server_id} configuration saved/updated!")

api_endpoints = {

    "predator": f"https://api.mozambiquehe.re/predator?auth={ApexAPIKey}",
    "map": f"https://api.mozambiquehe.re/maprotation?auth={ApexAPIKey}&version=2",
    "server": f"https://api.mozambiquehe.re/servers?auth={ApexAPIKey}&version=2"
    
}

#map to store json objects from each endpoint
responses = {}
for key, url in api_endpoints.items():
    resp = requests.get(url)
    responses[key] = resp.json()

map_data = responses["map"]
ltm_data = map_data['ltm']

server_data = responses["server"]


predator_data = responses["predator"]
predcap_data = predator_data['RP']

matchmaking_server_data = server_data['EA_novafusion']
crossplay_server_data = server_data['ApexOauth_Crossplay']
console_server_data = server_data['otherPlatforms']


# function to return player stats embed
async def create_player_stats_embed(platform, apex_uid,formatted_time):
    url = f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&uid={apex_uid}&platform={platform}"
    resp = requests.get(url)
    player_data = resp.json()
    global_data = player_data['global']
    ranked_data = global_data['rank']

    if platform == "PC":
        predcap_value = predcap_data['PC']['val']
    elif platform == "X1":
        predcap_value = predcap_data['X1']['val']
    elif platform == "PS4":
        predcap_value = predcap_data['PS4']['val']
    player_embed = discord.Embed(
        title=f"🎮 **__APEX LEGENDS STATS__**",
        description=f"**Player:** `{global_data['name']}`\n**UID:** `{global_data['uid']}`",
        colour=discord.Colour.gold() if "predator" in ranked_data['rankName'].lower() else 
                discord.Colour.purple() if "master" in ranked_data['rankName'].lower() else 
                discord.Colour.blue() if "diamond" in ranked_data['rankName'].lower() else 
                discord.Colour.teal() if "platinum" in ranked_data['rankName'].lower() else 
                discord.Colour.green() if "gold" in ranked_data['rankName'].lower() else 
                discord.Colour.light_grey() if "silver" in ranked_data['rankName'].lower() else 
                discord.Colour.dark_grey() if "bronze" in ranked_data['rankName'].lower() else 
                discord.Colour.default()
    )

    # Personal Stats Section
    player_embed.add_field(
        name="📊 **__RANKED STATS__**",
        value="",
        inline=False
    )

    player_embed.add_field(
        name="🏆 Current Rank",
        value=f"```{ranked_data['rankName']} {ranked_data['rankDiv']}```",
        inline=True
    )

    player_embed.add_field(
        name="🌟 Rank Points",
        value=f"```{ranked_data['rankScore']} RP```",
        inline=True
    )

    if ranked_data['rankScore'] < predcap_value:
        rp_until_pred = predcap_value - ranked_data['rankScore']
    else: 
        rp_until_pred = 0
        player_embed.add_field(
            name="🎯 RP to Predator",
            value=f"```{rp_until_pred} RP```",
            inline=True
        )

    # Map & Server Info Section
    player_embed.add_field(
        name="🗺️ **__MAP ROTATION__**",
        value="",
        inline=False
    )

    player_embed.add_field(
        name="LTM",
        value=f"```{ltm_data['current']['eventName']}```",
        inline=True
    )

    player_embed.add_field(
        name="⏱️ Time Remaining",
        value=f"```{ltm_data['current']['remainingMins']}m```",
        inline=True
    )
    player_embed.add_field(
        name="Next LTM",
        value=f"```{ltm_data['next']['eventName']}```",
        inline=True
    )


    player_embed.add_field(
        name="Ranked Map",
        value=f"```{map_data['ranked']['current']['map']}```",
        inline=True
    )

    player_embed.add_field(
        name="⏰ Time Remaining",
        value=f"```{round(map_data['ranked']['current']['remainingMins']/60, 1)}h```",
        inline=True
    )

    player_embed.add_field(
        name="Next Map",
        value=f"```{map_data['ranked']['next']['map']}```",
        inline=True
    )

    # Server Info Section
    player_embed.add_field(
        name="📈 **__SERVER INFO__**",
        value="",
        inline=False
    )

    player_embed.add_field(
        name="🏆 Predator Cap",
        value=f"```{predcap_value} RP```",
        inline=True
    )

    player_embed.add_field(
        name="🌍 Platform",
        value=f"```{platform}```",
        inline=True
    )

    player_embed.set_footer(
        text=f"last updated {formatted_time} ET"
    )
        # Set thumbnail
    rank_img_url = ranked_data.get('rankImg', None)
    if rank_img_url:
        player_embed.set_thumbnail(url=rank_img_url)
        # Also set author with player name and rank icon
        player_embed.set_author(name=f"{global_data['name']}'s Profile", 
        icon_url=rank_img_url)
    else:
        player_embed.set_author(name=f"{global_data['name']}'s Profile")
    return player_embed


# Boilerplate event: on_ready
@bot.event
async def on_ready():
    await bot.tree.sync() # Sync commands with Discord
    
    print(f'✅ {bot.user.name} is online and connected to Discord!')







@bot.tree.command(name="stats", description="Sends an embed with player stats that updates every X minutes")
async def stats(interaction: discord.Interaction):
    stats_channel = interaction.channel  # Use interaction.channel directly
    discord_id = interaction.user.id

    # Update current_RP
    async with aiosqlite.connect('server.db') as db:
        async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
            user = await cursor.fetchone()

        if user is None:
            await interaction.response.send_message("❌ You are not registered. Please use /register command first.", ephemeral=True)
            return

        # Use tuple unpacking for the user data
        discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user

        # Add timestamp and footer
        et = timezone(timedelta(hours=-5))  
        now_et = datetime.now(et)
        formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")

        try:
            stats_embed = await create_player_stats_embed(platform, apex_uid, formatted_time)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create stats embed: {e}", ephemeral=True)
            return

        try:
            if stats_message_id:
                # If a stats message already exists, fetch and edit it
                try:
                    stats_message = await stats_channel.fetch_message(stats_message_id)
                    await stats_message.edit(embed=stats_embed)
                except discord.NotFound:
                    # If the message is not found, send a new one
                    stats_message = await stats_channel.send(embed=stats_embed)
            else:
                # If no stats message exists, send a new one
                stats_message = await stats_channel.send(embed=stats_embed)

            # Update the database with the new message and channel IDs
            await db.execute(
                "UPDATE users SET stats_message_id = ?, stats_channel_id = ? WHERE discord_id = ?",
                (stats_message.id, stats_channel.id, discord_id)
            )
            await db.commit()

            await interaction.response.send_message("✅ Stats updated successfully!", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot lacks permissions to send messages in this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to send stats message: {e}", ephemeral=True)
        


        await db.execute(
            "UPDATE users SET stats_message_id = ?,stats_channel_id = ? WHERE discord_id = ?",
            (stats_message.id,stats_channel.id, discord_id)
        )
        await db.commit()


#not necessary since on_guild_join event handles this now
@bot.tree.command(name="register_server_id", description="Saves server ID and configuration to the database")
@app_commands.checks.has_role(admin)
async def register_server_id(interaction: discord.Interaction):
    discord_server_id = interaction.guild.id

    async with aiosqlite.connect('server.db') as db:
        await save_server_config(db, discord_server_id=discord_server_id)
        await db.commit()

    await interaction.response.send_message(f"✅ Server ID {discord_server_id} and configuration saved to the database!", ephemeral=True)

@bot.tree.command(name="register_server_status", description="Registers server status channel and updates the status message")
@app_commands.checks.has_role(admin)
async def register_server_status(interaction: discord.Interaction):
    apex_server_status_channel = interaction.channel.id

    async with aiosqlite.connect('server.db') as db:
        async with db.execute("SELECT apex_server_message_id FROM servers WHERE discord_server_id = ?", (interaction.guild.id,)) as cursor:
            row = await cursor.fetchone()

        apex_server_message_id = row[0] if row else None

        await save_server_config(db=db, discord_server_id=interaction.guild.id, apex_server_channel_id=apex_server_status_channel)
        await db.commit()

    await interaction.response.send_message(f"Server status channel ID {apex_server_status_channel} saved to database!", ephemeral=True)

    channel = bot.get_channel(apex_server_status_channel)
    if not channel:
        await interaction.followup.send("❌ Could not find the specified channel.", ephemeral=True)
        return

    # Define a dictionary to map server statuses to emojis
    status_emojis = {
        "UP": "🟢",  
        "DOWN": "🔴",  
        "SLOW": "🟡", 
        "UNKNOWN": "⚪"  
    }

    # Define a dictionary to map regions to flags
    region_flags = {
        "US-EAST": ":flag_us:",
        "US-WEST": ":flag_us:",
        "US-CENTRAL": ":flag_us:",
        "EU-EAST": ":flag_eu:",
        "EU-WEST": ":flag_eu:",
        "EU-CENTRAL": ":flag_eu:",
        "ASIA": "🌏",
        "SOUTHAMERICA": "🌍"
    }

    server_embed = discord.Embed(
        title=" **APEX LEGENDS SERVER STATUS**",
        description="Real-time server status and connectivity",
        colour=discord.Colour.blue()  
    )

    # Matchmaking Server Status Section
    server_embed.add_field(
        name="🛠️ **___MATCHMAKING SERVERS___**",
        value="",
        inline=False
    )

    for region, data in matchmaking_server_data.items():
        status = data['Status'].upper()  # Get the status and convert to uppercase
        emoji = status_emojis.get(status, "⚪")  # Default to white circle if status is unknown
        flag = region_flags.get(region.upper(), "❓")  # Default to question mark if region is unknown
        server_embed.add_field(
            name=f"{flag} {region}",
            value=f"```{emoji} {status}```",
            inline=True
        )

    # Crossplay Server Status Section
    server_embed.add_field(
        name="🔗 **___CROSSPLAY SERVERS___**",
        value="",
        inline=False
    )

    for region, data in crossplay_server_data.items():
        status = data['Status'].upper()
        emoji = status_emojis.get(status, "⚪")
        flag = region_flags.get(region.upper(), "❓")
        server_embed.add_field(
            name=f"{flag} {region}",
            value=f"```{emoji} {status}```",
            inline=True
        )

    # Console Server Status Section
    server_embed.add_field(
        name="🎮 **___CONSOLE SERVERS___**",
        value="",
        inline=False
    )

    for platform, data in console_server_data.items():
        status = data['Status'].upper()
        emoji = status_emojis.get(status, "⚪")
        server_embed.add_field(
            name=f"{platform}",
            value=f"```{emoji} {status}```",
            inline=True
        )

    # Add timestamp and footer (matching your original format)
    now_et = datetime.now(et)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")

    server_embed.set_footer(
        text=f"last updated {formatted_time} ET"
    )

    # Set thumbnail (using Apex logo or any relevant image)
    rank_img_url = "https://upload.wikimedia.org/wikipedia/commons/b/b1/Apex_legends_simple_logo.jpg"
    server_embed.set_thumbnail(url=rank_img_url)

    # Check if a message already exists and edit it, otherwise send a new one
    if apex_server_message_id:
        try:
            message = await channel.fetch_message(apex_server_message_id)
            await message.edit(embed=server_embed)
        except discord.NotFound:
            message = await channel.send(embed=server_embed)
    else:
        message = await channel.send(embed=server_embed)

    # Update the database with the new message ID
    async with aiosqlite.connect('server.db') as db:
        await db.execute(
            "UPDATE servers SET apex_server_message_id = ? WHERE discord_server_id = ?",
            (message.id, interaction.guild.id)
        )
        await db.commit()
#needs to throw error if the user is registered already (done by checking discord id)
@bot.tree.command(name="register", description="Registers your Apex UID and server ID(for xbox/ps use gamertag & pc use Origin gamertag)")
async def register_user(interaction: discord.Interaction, gamertag: str, platform: str):
    discord_id = interaction.user.id
    discord_server_id = interaction.guild.id

    playerURL=f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&player={gamertag}&platform={platform}"

    playerresp = requests.get(playerURL)
    playerData = playerresp.json()
    apex_uid = playerData['global']['uid']

    async with aiosqlite.connect('server.db') as db:
        await db.execute('''
            INSERT INTO users (discord_id, discord_server_id, apex_uid, platform, current_RP)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                discord_server_id=excluded.discord_server_id,
                apex_uid=excluded.apex_uid,
                platform=excluded.platform
        ''', (discord_id, discord_server_id, apex_uid, platform, 0))
        await db.commit()

    await interaction.response.send_message(f"✅ Your Apex UID `{apex_uid}` and server ID `{platform}` have been registered!", ephemeral=True)


#add a unregister command if you need to change your apex uid or server id later


@bot.tree.command(name="start_tracking", description="Starts tracking your Apex RP")
async def start_tracking(interaction: discord.Interaction):
    discord_id = interaction.user.id
    async with aiosqlite.connect('server.db') as db:
        async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
            user = await cursor.fetchone()

    if user is None:
        await interaction.response.send_message("❌ You are not registered. Please use /register command first.", ephemeral=True)
        return

    # Use tuple unpacking for the user data
    discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user

    # Query Apex API
    playerURL = f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&uid={apex_uid}&platform={platform}"
    try:
        playerresp = requests.get(playerURL)
        playerresp.raise_for_status()
        playerData = playerresp.json()
        apex_rp = int(playerData['global']['rank']['rankScore'])
    except Exception as e:
        await interaction.response.send_message(f"Failed to fetch RP from API: {e}", ephemeral=True)
        return

    # Update current_RP
    async with aiosqlite.connect('server.db') as db:
        await db.execute(
            "UPDATE users SET current_RP = ?, time_registered = ? WHERE discord_id = ?",
            (apex_rp, datetime.now(et), discord_id)
        )
        await db.commit()

    await interaction.response.send_message(f"Tracking started — current RP: {apex_rp}", ephemeral=True)
    
@bot.tree.command(name="stop_tracking", description="Stops tracking your Apex RP")
async def stop_tracking(interaction: discord.Interaction):
    discord_id = interaction.user.id
    async with aiosqlite.connect('server.db') as db:
        async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
            user = await cursor.fetchone()

    if user is None:
        await interaction.response.send_message("❌ You are not registered. Please use /register command first.", ephemeral=True)
        return

    # Use tuple unpacking for the user data
    discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user

    # Parse the stored time_registered string into a datetime object
    if time_registered:
        time_registered = datetime.fromisoformat(time_registered)
    else:
        await interaction.response.send_message("❌ No tracking start time found. Please start tracking first.", ephemeral=True)
        return

    # Calculate time difference
    time_played = format_time_difference(time_registered, datetime.now(et))

    # Query Apex API
    playerURL = f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&uid={apex_uid}&platform={platform}"
    try:
        playerresp = requests.get(playerURL)
        playerresp.raise_for_status()
        playerData = playerresp.json()
        apex_rp = int(playerData['global']['rank']['rankScore'])
    except Exception as e:
        await interaction.response.send_message(f"Failed to fetch RP from API: {e}", ephemeral=True)
        return

    # Update current_RP
    async with aiosqlite.connect('server.db') as db:
        await db.execute(
            "UPDATE users SET current_RP = ?, time_registered = NULL WHERE discord_id = ?",
            (apex_rp, discord_id)
        )
        await db.commit()

    if current_RP < apex_rp:
        rp_gained = apex_rp - current_RP
        await interaction.response.send_message(f"Tracking ended — current RP: {apex_rp}. Gained {rp_gained} RP in {time_played}", ephemeral=True)
    elif current_RP > apex_rp:   
        rp_lost = current_RP - apex_rp
        await interaction.response.send_message(f"Tracking ended — current RP: {apex_rp}. Lost {rp_lost} RP in {time_played}", ephemeral=True)
    else:
        await interaction.response.send_message(f"Tracking ended — current RP: {apex_rp}. No RP gained or lost in {time_played}", ephemeral=True)
    
    
bot.run(DiscordTOKEN)



# THINGS TO CONSIDER FOR FUTURE UPDATES

#Priority 1
# get rid of hardcoded debug statements and implement a loop to update player stats every X minutes
# implement error handling for api requests
#add steam api usage for automatic rp tracking on pc platform

#Priority 2
# implement unregister command to delete user from db
# implement command to view current registered info
# implement command to view current tracked rp and time registered
# implement leaderboard command to view top 3 players in server by rp 
# implement command to change apex uid or platform
# implement periodic task to update server status message in each server's registered status channel
# implement periodic task to update each user's tracked rp and notify them of changes
# implement command to view current map rotation and server status without player stats