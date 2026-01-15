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

# Automatically save new server config when bot joins a server
@bot.event
async def on_guild_join(guild):
    save_server_config(
        server_id=guild.id,
        server_status=None
    )
    print(f"✅ Joined new server: {guild.name} ({guild.id}) and added to database.")

# Initialize the database
def init_db():
    db = sqlite3.connect('server.db')
    c = db.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            server_id INTEGER PRIMARY KEY,     -- Each Discord server has unique ID (like social security number)
            server_status INTEGER        -- Store channel ID for server status
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            discord_id INTEGER PRIMARY KEY, -- Each Discord user has unique ID
            discord_server_id INTEGER,              -- Foreign key to link user to a server
            apex_uid TEXT,                 -- Store Apex Legends UID
            apex_server_id INTEGER,         -- Store server ID for Apex Legends
            current_RP INTEGER              -- Store current RP of the user
        )
    ''')
    db.commit()
    db.close()
    print("✅ Database created and ready!")

# save or update server config
def save_server_config(server_id, server_status=None):
    """Insert or update server config. Only overwrite columns when a non-None value is provided.

    Usage:
      save_server_config(server_id, server_status=123)
    will update only the server_status for that server and preserve other fields.
    """
    db = sqlite3.connect('server.db')
    c = db.cursor()

    # Check if a row already exists for this server
    c.execute('SELECT server_status FROM servers WHERE server_id = ?', (server_id,))
    row = c.fetchone()

    if row is None:
        # No existing row — insert whatever values were provided (others will be NULL)
        c.execute('''
            INSERT INTO servers (server_id, server_status)
            VALUES (?, ?)
        ''', (server_id, server_status))
    else:
        cur_status = row[0]
        new_status = server_status if server_status is not None else cur_status

        c.execute('''
            UPDATE servers
            SET server_status = ?
            WHERE server_id = ?
        ''', (new_status, server_id))

    db.commit()
    db.close()
    print(f"✅ Server {server_id} configuration saved/updated!")

#hard coded token login
api_endpoints = {

    #make sure to remove this hardcoding later
    "player2": f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&player=TheCloutFarmer&platform=PC",
    "player": f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&player=TheCloutFarmer&platform=PC",
    "predator": f"https://api.mozambiquehe.re/predator?auth={ApexAPIKey}&platform=PC",
    "map": f"https://api.mozambiquehe.re/maprotation?auth={ApexAPIKey}&version=2",
    "server": f"https://api.mozambiquehe.re/servers?auth={ApexAPIKey}&version=2"
    
}

#map to store json objects from each endpoint
responses = {}
for key, url in api_endpoints.items():
    resp = requests.get(url)
    responses[key] = resp.json()

player2_data = responses["player2"]
player_data = responses["player"]

predator_data = responses["predator"]
map_data = responses["map"]
server_data = responses["server"]

global_data = player2_data['global']
ranked_data = global_data['rank']
predcap_data = predator_data['RP']
matchmaking_server_data = server_data['EA_novafusion']
crossplay_server_data = server_data['ApexOauth_Crossplay']
console_server_data = server_data['otherPlatforms']




# Boilerplate event: on_ready
@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync() 


#ALL DEBUGGING PRINT STATEMENTS
    print("player: " + global_data['name'])
    print("UID: " + global_data['uid'])
    print("Current RP: " + str(ranked_data['rankScore']))
    rankdiv = ranked_data['rankDiv']
    if rankdiv == 0:
        rankdiv = ""
    print("Current Rank: " + ranked_data['rankName']+ " " + str(rankdiv))
    print(ranked_data['rankImg'])
    print("Predator Cap: " + str(predcap_data['PC']['val']))
    print("current ranked map: "+ map_data['ranked']['current']['map'])
    print("next ranked map: "+ map_data['ranked']['next']['map']+ " in "+ str(round(map_data['ranked']['current']['remainingMins']/60,1)) + " hours")
    
    
    print("matchmaking server status")
    print("US-East: " + matchmaking_server_data['US-East']['Status'])
    print("US-West: " + matchmaking_server_data['US-West']['Status'])
    print("US-Central: " + matchmaking_server_data['US-Central']['Status'])

    print("Crossplay server status")
    print("US-East: " + crossplay_server_data['US-East']['Status'])
    print("US-West: " + crossplay_server_data['US-West']['Status'])
    print("US-Central: " + crossplay_server_data['US-Central']['Status'])

    print("Console server status")
    print("Xbox-Live: " + console_server_data['Xbox-Live']['Status'])
    print("Playstation: " + console_server_data['Playstation-Network']['Status'])


#ALL DEBUGGING PRINT STATEMENTS


    player_embed = discord.Embed(
        title=f"🎮 **APEX LEGENDS STATS**",
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
        name="📊 **RANKED STATS**",
        value="────────────────",
        inline=False
    )

    player_embed.add_field(
        name="🏆 Current Rank",
        value=f"**{ranked_data['rankName']} {rankdiv}**",
        inline=True
    )

    player_embed.add_field(
        name="🔢 Rank Points",
        value=f"**{ranked_data['rankScore']:,}** RP",
        inline=True
    )

    if ranked_data['rankScore'] < predcap_data['PC']['val']:
        rp_until_pred = predcap_data['PC']['val'] - ranked_data['rankScore']
        player_embed.add_field(
            name="🎯 RP to Predator",
            value=f"**{rp_until_pred:,}** RP",
            inline=True
        )

    # Map & Server Info Section
    player_embed.add_field(
        name="🗺️ **MAP ROTATION**",
        value="────────────────",
        inline=False
    )

    player_embed.add_field(
        name="Current Map",
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
        name="📈 **SERVER INFO**",
        value="────────────────",
        inline=False
    )

    player_embed.add_field(
        name="🏆 Predator Cap",
        value=f"**{predcap_data['PC']['val']:,}** RP",
        inline=True
    )

    player_embed.add_field(
        name="🌍 Platform",
        value="**PC**",
        inline=True
    )

    # Add timestamp and footer
    et = timezone(timedelta(hours=-5))  
    now_et = datetime.now(et)

    formatted_time = now_et.strftime("%I:%M %p").lstrip("0")

    player_embed.set_footer(
        text=f"updated today at {formatted_time} ET"
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

    # Send to channel
    CHANNEL_ID = 1443272151997350041 
    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        #Store message ID for future updates instead of purging
        try:
            # Try to find existing bot message to edit instead of purge
            async for message in channel.history(limit=10):
                if message.author == bot.user:
                    await message.edit(embed=player_embed)
                    break
            else:
                # No existing message found, send new one
                await channel.send(embed=player_embed)
        except discord.Forbidden:
            print(f"Missing permissions in channel {CHANNEL_ID}")
        except discord.HTTPException as e:
            print(f"Failed to send message: {e}")

    print(f'✅ {bot.user.name} is online and connected to Discord!')






# Boilerplate command example
@bot.tree.command(name="testing", description="testing")
async def example(interaction: discord.Interaction):
    pass  # Add command logic here

@bot.tree.command(name="register_server_id", description="saves server id to database")
@app_commands.checks.has_role(admin)
async def serverid_slash(interaction: discord.Interaction):
    server_id = interaction.guild.id
    save_server_config(server_id=server_id, server_status=None)
    await interaction.response.send_message(f"Server ID {server_id} and configuration saved to database!", ephemeral=True)

@bot.tree.command(name="register_server_status", description="registers server status channel")
@app_commands.checks.has_role(admin)
async def register_server_status(interaction: discord.Interaction):
    server_status_channel_id = interaction.channel.id
    save_server_config(server_id=interaction.guild.id, server_status=server_status_channel_id)
    await interaction.response.send_message(f"Server status channel ID {server_status_channel_id} saved to database!", ephemeral=True)
    channel = bot.get_channel(server_status_channel_id)


    server_embed = discord.Embed(
    title=" **APEX LEGENDS SERVER STATUS**",
    description="Real-time server status and connectivity",
    colour=discord.Colour.blue()  # Or choose your preferred color
)

    # Matchmaking Server Status Section
    server_embed.add_field(
        name="🛠️ **MATCHMAKING SERVERS**",
        value="────────────────",
        inline=False
    )

    server_embed.add_field(
        name="🇺🇸 US-East",
        value=f"```{matchmaking_server_data['US-East']['Status']}```",
        inline=True
    )

    server_embed.add_field(
        name="🇺🇸 US-West",
        value=f"```{matchmaking_server_data['US-West']['Status']}```",
        inline=True
    )

    server_embed.add_field(
        name="🇺🇸 US-Central",
        value=f"```{matchmaking_server_data['US-Central']['Status']}```",
        inline=True
    )

    # Crossplay Server Status Section
    server_embed.add_field(
        name="🔗 **CROSSPLAY SERVERS**",
        value="────────────────",
        inline=False
    )

    server_embed.add_field(
        name="🇺🇸 US-East",
        value=f"```{crossplay_server_data['US-East']['Status']}```",
        inline=True
    )

    server_embed.add_field(
        name="🇺🇸 US-West",
        value=f"```{crossplay_server_data['US-West']['Status']}```",
        inline=True
    )

    server_embed.add_field(
        name="🇺🇸 US-Central",
        value=f"```{crossplay_server_data['US-Central']['Status']}```",
        inline=True
    )

    # Console Server Status Section
    server_embed.add_field(
        name="🎮 **CONSOLE SERVERS**",
        value="────────────────",
        inline=False
    )

    server_embed.add_field(
        name="Xbox Live",
        value=f"```{console_server_data['Xbox-Live']['Status']}```",
        inline=True
    )

    server_embed.add_field(
        name="PlayStation",
        value=f"```{console_server_data['Playstation-Network']['Status']}```",
        inline=True
    )

    # Add timestamp and footer (matching your original format)
    et = timezone(timedelta(hours=-5))  
    now_et = datetime.now(et)
    formatted_time = now_et.strftime("%I:%M %p").lstrip("0")

    server_embed.set_footer(
        text=f"updated today at {formatted_time} ET"
)
    # Set thumbnail (using Apex logo or any relevant image)
    rank_img_url = "https://upload.wikimedia.org/wikipedia/commons/b/b1/Apex_legends_simple_logo.jpg"
    server_embed.set_thumbnail(url=rank_img_url)

    await channel.send(embed=server_embed)

#needs to throw error if the user is registered already (done by checking discord id)
@bot.tree.command(name="register", description="Registers your Apex UID and server ID(for xbox/ps use gamertag & pc use Origin gamertag)")
async def register_user(interaction: discord.Interaction, gamertag: str, platform: str):
    discord_id = interaction.user.id
    discord_server_id = interaction.guild.id

    playerURL=f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&player={gamertag}&platform={platform}"

    playerresp = requests.get(playerURL)
    playerData = playerresp.json()
    apex_uid = playerData['global']['uid']
    
    db = sqlite3.connect('server.db')
    c = db.cursor()

    # Insert or update user info
    c.execute('''
        INSERT INTO users (discord_id, discord_server_id, apex_uid, apex_server_id, current_RP)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET
            discord_server_id=excluded.discord_server_id,
            apex_uid=excluded.apex_uid,
            apex_server_id=excluded.apex_server_id
    ''', (discord_id, discord_server_id, apex_uid, platform, 0))

    db.commit()
    db.close()

    await interaction.response.send_message(f"✅ Your Apex UID `{apex_uid}` and server ID `{platform}` have been registered!", ephemeral=True)


#add a unregister command if you need to change your apex uid or server id later


@bot.tree.command(name="startTracking", description="Starts tracking your Apex RP")
async def start_tracking(interaction: discord.Interaction):


    
    playerURL=f"https://api.mozambiquehe.re/bridge?auth={ApexAPIKey}&player={gamertag}&platform={platform}"

    playerresp = requests.get(playerURL)
    playerData = playerresp.json()
    apex_uid = playerData['global']['uid']
    
    await interaction.response.send_message("Tracking started! (Functionality to be implemented)", ephemeral=True)

bot.run(DiscordTOKEN)
