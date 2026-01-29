"""
Periodic tasks for the WayPoint Discord bot using discord.ext.tasks.
"""
import discord
from discord.ext import tasks
from datetime import datetime
from config import TIMEZONE_ET
from embeds import create_player_stats_embed, create_server_status_embed


# Global references (will be set by setup_tasks)
bot = None
db = None
api = None


@tasks.loop(minutes=1)
async def update_stats_periodically():
    """Update player stats embeds every minute."""
    try:
        await api.fetch_all_data()  # Re-fetch API data
        
        users = await db.get_all_users()
        
        for user in users:
            discord_id, discord_server_id, apex_uid, platform, current_RP, time_registered, stats_message_id, stats_channel_id = user
            
            # Skip if no message ID set
            if not stats_message_id or not stats_channel_id:
                continue
            
            # Fetch the channel
            channel = bot.get_channel(stats_channel_id)
            if channel is None:
                print(f"❌ Could not find channel ID {stats_channel_id} for user {discord_id}")
                continue
            
            # Fetch the message
            try:
                message = await channel.fetch_message(stats_message_id)
            except discord.NotFound:
                print(f"❌ Could not find message ID {stats_message_id} in channel ID {stats_channel_id} for user {discord_id}")
                continue
            
            # Create updated embed
            now_et = datetime.now(TIMEZONE_ET)
            formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
            
            try:
                updated_embed = await create_player_stats_embed(platform, apex_uid, formatted_time, api)
            except Exception as e:
                print(f"❌ Failed to create stats embed for user {discord_id}: {e}")
                continue
            
            # Edit the message
            try:
                await message.edit(embed=updated_embed)
                print(f"✅ Updated stats message for user {discord_id}")
            except discord.Forbidden:
                print(f"❌ Bot lacks permissions to edit message ID {stats_message_id} in channel ID {stats_channel_id} for user {discord_id}")
            except discord.HTTPException as e:
                print(f"❌ Failed to edit stats message for user {discord_id}: {e}")
    
    except Exception as e:
        print(f"❌ Error in update_stats_periodically: {e}")


@tasks.loop(minutes=5)
async def update_server_stats_periodically():
    """Update server status embeds every 5 minutes."""
    try:
        await api.fetch_all_data()  # Re-fetch API data
        
        servers = await db.get_all_servers()
        
        for server in servers:
            discord_server_id, apex_server_channel_id, apex_server_message_id = server
            
            # Skip if no message ID set
            if not apex_server_channel_id or not apex_server_message_id:
                continue
            
            # Fetch the channel
            channel = bot.get_channel(apex_server_channel_id)
            if channel is None:
                print(f"❌ Could not find channel ID {apex_server_channel_id} for server {discord_server_id}")
                continue
            
            # Fetch the message
            try:
                message = await channel.fetch_message(apex_server_message_id)
            except discord.NotFound:
                print(f"❌ Could not find message ID {apex_server_message_id} in channel ID {apex_server_channel_id} for server {discord_server_id}")
                continue
            
            # Create updated embed
            now_et = datetime.now(TIMEZONE_ET)
            formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
            
            updated_embed = create_server_status_embed(formatted_time, api)
            
            # Edit the message
            try:
                await message.edit(embed=updated_embed)
                print(f"✅ Updated server status message for server {discord_server_id}")
            except discord.Forbidden:
                print(f"❌ Bot lacks permissions to edit message ID {apex_server_message_id} in channel ID {apex_server_channel_id} for server {discord_server_id}")
            except discord.HTTPException as e:
                print(f"❌ Failed to edit server status message for server {discord_server_id}: {e}")
    
    except Exception as e:
        print(f"❌ Error in update_server_stats_periodically: {e}")


@update_stats_periodically.before_loop
async def before_update_stats():
    """Wait for the bot to be ready before starting the stats update loop."""
    await bot.wait_until_ready()


@update_server_stats_periodically.before_loop
async def before_update_server_stats():
    """Wait for the bot to be ready before starting the server stats update loop."""
    await bot.wait_until_ready()


@update_stats_periodically.error
async def stats_error_handler(error):
    """Handle errors in the stats update task."""
    print(f"❌ Stats update task error: {error}")


@update_server_stats_periodically.error
async def server_stats_error_handler(error):
    """Handle errors in the server stats update task."""
    print(f"❌ Server stats update task error: {error}")


def setup_tasks(bot_instance, db_instance, api_instance):
    """
    Initialize and start all periodic tasks.
    
    Args:
        bot_instance: The Discord bot instance
        db_instance: The Database instance
        api_instance: The API instance
    """
    global bot, db, api
    bot = bot_instance
    db = db_instance
    api = api_instance
    
    # Start tasks if not already running
    if not update_stats_periodically.is_running():
        update_stats_periodically.start()
        print("✅ Started stats update task")
    
    if not update_server_stats_periodically.is_running():
        update_server_stats_periodically.start()
        print("✅ Started server stats update task")
