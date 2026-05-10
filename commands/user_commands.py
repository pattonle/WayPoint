"""
User-facing commands for the WayPoint Discord bot.
"""
import discord
from discord import app_commands
from datetime import datetime
from config import TIMEZONE_ET, ADMIN_ROLE
from embeds import create_player_stats_embed, create_admin_stats_embed
from utils import format_time_difference, format_rp_per_hour
from api import get_steam_player_async



# Module-level variables (will be set by setup)
bot = None
db = None
api = None


async def setup(bot_instance, db_instance, api_instance):
    """
    Register all user commands with the bot.
    
    Args:
        bot_instance: Discord bot instance
        db_instance: Database instance
        api_instance: API instance
    """
    global bot, db, api
    bot = bot_instance
    db = db_instance
    api = api_instance
    
    # Register commands
    bot.tree.add_command(register_user)
    bot.tree.add_command(stats)
    bot.tree.add_command(track)
    bot.tree.add_command(setsteam)
    
    print("✅ User commands registered")


@app_commands.command(name="register", description="Registers your Apex UID and server ID(for xbox/ps use gamertag & pc use Origin gamertag)")
async def register_user(interaction: discord.Interaction, gamertag: str, platform: str):
    """
    Register a user with their Apex Legends gamertag and platform.
    
    Args:
        interaction: Discord interaction
        gamertag: Player's gamertag
        platform: Gaming platform (PC, PS4, X1)
    """
    discord_id = interaction.user.id
    discord_server_id = interaction.guild.id
    
    try:
        # Get Apex UID from gamertag
        apex_uid = await api.get_apex_uid(gamertag, platform)
        
        # Save user to database
        await db.save_user(discord_id, discord_server_id, apex_uid, platform, 0)
        
        await interaction.response.send_message(
            f"✅ Your Apex UID `{apex_uid}` and platform `{platform}` have been registered!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to register: {e}",
            ephemeral=True
        )


@app_commands.command(name="stats", description="Sends an embed with player stats that updates every X minutes")
async def stats(interaction: discord.Interaction):
    """
    Display player statistics in an auto-updating embed.
    
    Args:
        interaction: Discord interaction
    """
    stats_channel = interaction.channel
    discord_id = interaction.user.id
    
    # Get user from database
    user = await db.get_user(discord_id)
    
    if user is None:
        await interaction.response.send_message(
            "❌ You are not registered. Please use /register command first.",
            ephemeral=True
        )
        return
    
    # Unpack user data (support legacy and extended schemas)
    discord_id = user[0]
    discord_server_id = user[1] if len(user) > 1 else None
    apex_uid = user[2] if len(user) > 2 else None
    platform = user[3] if len(user) > 3 else None
    current_RP = user[4] if len(user) > 4 else None
    time_registered = user[5] if len(user) > 5 else None
    stats_message_id = user[6] if len(user) > 6 else None
    stats_channel_id = user[7] if len(user) > 7 else None
    
    # Acknowledge the interaction immediately
    await interaction.response.send_message("🔄 Updating your stats...", ephemeral=True, delete_after=2)
    
    # Create timestamp
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    
    try:
        #if any(role.name == ADMIN_ROLE for role in interaction.user.roles):
           # stats_embed = await create_admin_stats_embed(platform, apex_uid, formatted_time, api)
        #else:
            stats_embed = await create_player_stats_embed(platform, apex_uid, formatted_time, api)

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to create stats embed: {e}", ephemeral=True)
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
        await db.update_user_stats_message(discord_id, stats_message.id, stats_channel.id)
    
    except discord.Forbidden:
        await interaction.followup.send("❌ Bot lacks permissions to send messages in this channel.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Failed to send stats message: {e}", ephemeral=True)


@app_commands.command(name="track", description="Toggle tracking your Apex RP (start/stop)")
async def track(interaction: discord.Interaction):
    """Toggle RP tracking for the calling user.

    If tracking is not active, this command stores the current RP and start time.
    If tracking is active, this command fetches current RP, reports gain/loss,
    and clears the start time.

    Args:
        interaction: Discord interaction
    """
    discord_id = interaction.user.id
    user = await db.get_user(discord_id)

    if user is None:
        await interaction.response.send_message(
            "❌ You are not registered. Please use /register command first.",
            ephemeral=True,
        )
        return

    discord_id = user[0]
    discord_server_id = user[1] if len(user) > 1 else None
    apex_uid = user[2] if len(user) > 2 else None
    platform = user[3] if len(user) > 3 else None
    current_RP = user[4] if len(user) > 4 else None
    time_registered = user[5] if len(user) > 5 else None
    stats_message_id = user[6] if len(user) > 6 else None
    stats_channel_id = user[7] if len(user) > 7 else None

    # Fetch current RP from API
    try:
        player_data = await api.fetch_player_stats(apex_uid, platform)
        apex_rp = int(player_data["global"]["rank"]["rankScore"])
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to fetch RP from API: {e}", ephemeral=True)
        return

    # If time_registered is set, tracking is active -> stop tracking
    if time_registered:
        if isinstance(time_registered, str):
            try:
                start_time = datetime.fromisoformat(time_registered)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Tracking start time in DB is invalid. Please run /track again to reset.",
                    ephemeral=True,
                )
                # Reset tracking state to something sane
                await db.update_user_tracking(discord_id, apex_rp, None)
                return
        else:
            start_time = time_registered

        end_time = datetime.now(TIMEZONE_ET)
        time_played = format_time_difference(start_time, end_time)
        rp_change = apex_rp - current_RP if current_RP is not None else 0
        avg_rp_per_hour = format_rp_per_hour(rp_change, start_time, end_time)

        # Update current RP and clear tracking start time
        await db.update_user_tracking(discord_id, apex_rp, None)

        if current_RP is None:
            await interaction.response.send_message(
                f"✅ Tracking ended — current RP: {apex_rp}. Played for {time_played}",
                ephemeral=True,
            )
            return

        if current_RP < apex_rp:
            await interaction.response.send_message(
                f"✅ Tracking ended — current RP: {apex_rp}. Gained {apex_rp - current_RP} RP in {time_played} ({avg_rp_per_hour})",
                ephemeral=True,
            )
        elif current_RP > apex_rp:
            await interaction.response.send_message(
                f"✅ Tracking ended — current RP: {apex_rp}. Lost {current_RP - apex_rp} RP in {time_played} ({avg_rp_per_hour})",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ Tracking ended — current RP: {apex_rp}. No RP gained or lost in {time_played} ({avg_rp_per_hour})",
                ephemeral=True,
            )

        return

    # Otherwise, tracking is inactive -> start tracking
    await db.update_user_tracking(discord_id, apex_rp, datetime.now(TIMEZONE_ET))
    await interaction.response.send_message(f"✅ Tracking started — current RP: {apex_rp}", ephemeral=True)


@app_commands.command(name="getsteam", description="Show your saved Steam profile (ephemeral)")
async def getsteam(interaction: discord.Interaction):
    """
    Display the invoking user's saved Steam info (name, id, avatar) ephemeral.
    """
    discord_id = interaction.user.id
    user = await db.get_user(discord_id)

    if user is None:
        await interaction.response.send_message("❌ You are not registered. Use /register first.", ephemeral=True)
        return

    # safe unpack
    steam_id = user[8] if len(user) > 8 else None

    if not steam_id:
        await interaction.response.send_message("❌ No Steam ID saved. Set one with /setsteam.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        player = await api.get_steam_player_async(steam_id)
    except Exception:
        player = None

    if player is None:
        await interaction.followup.send(f"⚠️ Steam ID {steam_id} saved but profile could not be fetched (may be private).", ephemeral=True)
        return

    persona = player.get('personaname', 'Unknown')
    avatar = player.get('avatarfull') or player.get('avatar')
    profile_url = f"https://steamcommunity.com/profiles/{player.get('steamid')}"

    embed = discord.Embed(title=f"Steam: {persona}", description=f"ID: {player.get('steamid')}\n[Profile]({profile_url})", color=discord.Colour.blue())
    if avatar:
        embed.set_thumbnail(url=avatar)

    await interaction.followup.send(embed=embed, ephemeral=True)


@app_commands.command(name="setsteam", description="Register your SteamID64 for Apex monitoring")
async def setsteam(interaction: discord.Interaction, steamid: str):
    """
    Save the invoking user's SteamID64 to the database for Apex play monitoring.
    """
    discord_id = interaction.user.id

    await interaction.response.defer(ephemeral=True)

    # Validate via Steam API (accepts SteamID64 or vanity)
    try:
        player = await api.get_steam_player_async(steamid)
    except Exception as e:
        player = None

    if player is None:
        await interaction.followup.send("❌ Could not validate that Steam ID/vanity exists. Please provide a valid SteamID64 or vanity name.", ephemeral=True)
        return

    resolved_steamid = player.get('steamid')
    persona = player.get('personaname')

    try:
        await db.update_user_steam_id(discord_id, resolved_steamid)
        await interaction.followup.send(f"✅ Saved Steam ID {resolved_steamid} for `{persona}`.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to save Steam ID: {e}", ephemeral=True)
