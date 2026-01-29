"""
User-facing commands for the WayPoint Discord bot.
"""
import discord
from discord import app_commands
from datetime import datetime
from config import TIMEZONE_ET
from embeds import create_player_stats_embed
from utils import format_time_difference


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
    bot.tree.add_command(start_tracking)
    bot.tree.add_command(stop_tracking)
    
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
    
    # Unpack user data
    discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user
    
    # Acknowledge the interaction immediately
    await interaction.response.send_message("🔄 Updating your stats...", ephemeral=True, delete_after=2)
    
    # Create timestamp
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    
    try:
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


@app_commands.command(name="start_tracking", description="Starts tracking your Apex RP")
async def start_tracking(interaction: discord.Interaction):
    """
    Start tracking a user's Apex Legends rank points.
    
    Args:
        interaction: Discord interaction
    """
    discord_id = interaction.user.id
    user = await db.get_user(discord_id)
    
    if user is None:
        await interaction.response.send_message(
            "❌ You are not registered. Please use /register command first.",
            ephemeral=True
        )
        return
    
    # Unpack user data
    discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user
    
    # Query Apex API for current RP
    try:
        player_data = await api.fetch_player_stats(apex_uid, platform)
        apex_rp = int(player_data['global']['rank']['rankScore'])
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to fetch RP from API: {e}", ephemeral=True)
        return
    
    # Update current_RP and tracking start time
    await db.update_user_tracking(discord_id, apex_rp, datetime.now(TIMEZONE_ET))
    
    await interaction.response.send_message(f"✅ Tracking started — current RP: {apex_rp}", ephemeral=True)


@app_commands.command(name="stop_tracking", description="Stops tracking your Apex RP")
async def stop_tracking(interaction: discord.Interaction):
    """
    Stop tracking a user's Apex Legends rank points and show gains/losses.
    
    Args:
        interaction: Discord interaction
    """
    discord_id = interaction.user.id
    user = await db.get_user(discord_id)
    
    if user is None:
        await interaction.response.send_message(
            "❌ You are not registered. Please use /register command first.",
            ephemeral=True
        )
        return
    
    # Unpack user data
    discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user
    
    # Parse the stored time_registered string into a datetime object
    if time_registered:
        time_registered = datetime.fromisoformat(time_registered)
    else:
        await interaction.response.send_message(
            "❌ No tracking start time found. Please start tracking first.",
            ephemeral=True
        )
        return
    
    # Calculate time difference
    time_played = format_time_difference(time_registered, datetime.now(TIMEZONE_ET))
    
    # Query Apex API for current RP
    try:
        player_data = await api.fetch_player_stats(apex_uid, platform)
        apex_rp = int(player_data['global']['rank']['rankScore'])
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to fetch RP from API: {e}", ephemeral=True)
        return
    
    # Update current_RP and clear tracking
    await db.update_user_tracking(discord_id, apex_rp, None)
    
    # Calculate RP difference
    if current_RP < apex_rp:
        rp_gained = apex_rp - current_RP
        await interaction.response.send_message(
            f"✅ Tracking ended — current RP: {apex_rp}. Gained {rp_gained} RP in {time_played}",
            ephemeral=True
        )
    elif current_RP > apex_rp:
        rp_lost = current_RP - apex_rp
        await interaction.response.send_message(
            f"✅ Tracking ended — current RP: {apex_rp}. Lost {rp_lost} RP in {time_played}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"✅ Tracking ended — current RP: {apex_rp}. No RP gained or lost in {time_played}",
            ephemeral=True
        )
