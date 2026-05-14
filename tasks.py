"""
Periodic tasks for the WayPoint Discord bot using discord.ext.tasks.
"""
import discord
from discord.ext import tasks
from datetime import datetime, time
from config import TIMEZONE_ET
from api import get_player_game_async
from embeds import create_player_stats_embed, create_server_status_embed
from utils import check_cpu_temp


# Global references (will be set by setup_tasks)
bot = None
db = None
api = None

test_id=


@tasks.loop(time=time(hour=9, minute=0, tzinfo=TIMEZONE_ET))
async def thermal_throttle_check():
    cpu_temp = check_cpu_temp()
    if cpu_temp is not None:
        user = await bot.fetch_user(test_id)
        await user.send(f"🤖Daily CPU Temperature: {cpu_temp.temperature:.1f}°C")
        pass


@thermal_throttle_check.before_loop
async def before_thermal_throttle_check():
    await bot.wait_until_ready()


@thermal_throttle_check.error
async def thermal_throttle_check_error_handler(error):
    """Handle errors in the thermal throttle check task."""
    print(f"❌ Thermal throttle check task error: {error}")


@tasks.loop(minutes=10)
async def thermal_throttle_alert():
    cpu_temp = check_cpu_temp()
    if cpu_temp is not None:
        user = await bot.fetch_user(test_id)
        if cpu_temp.temperature >= 80:
            await user.send(f"🚩 URGENT Warning: CPU temperature is at {cpu_temp.temperature:.1f}°C.")
        elif cpu_temp.temperature > 70 and cpu_temp.temperature < 80:
            await user.send(f"⚠️ Critical Warning: CPU temperature is at {cpu_temp.temperature:.1f}°C.")
        elif cpu_temp.temperature >= 65 and cpu_temp.temperature <= 70:
            await user.send(f"🚩Pi is running hottern than usual. CPU temperature is at {cpu_temp.temperature:.1f}°C.")

        pass


@thermal_throttle_alert.before_loop
async def before_thermal_throttle_alert():
    await bot.wait_until_ready()


@thermal_throttle_alert.error
async def thermal_throttle_alert_error_handler(error):
    """Handle errors in the thermal throttle alert task."""
    print(f"❌ Thermal throttle alert task error: {error}")

@tasks.loop(minutes=1)
async def update_stats_periodically():
    """Update player stats embeds every minute."""
    try:
        await api.fetch_all_data()  # Re-fetch API data
        
        users = await db.get_all_users()

        for user in users:
            # Handle multiple schema versions safely by index mapping
            # Expected columns: discord_id, discord_server_id, apex_uid, platform, current_RP,
            # time_registered, stats_message_id, stats_channel_id, steam_id, session_start_RP, session_start_time, is_in_game
            discord_id = user[0]
            discord_server_id = user[1] if len(user) > 1 else None
            apex_uid = user[2] if len(user) > 2 else None
            platform = user[3] if len(user) > 3 else None
            current_RP = user[4] if len(user) > 4 else None
            time_registered = user[5] if len(user) > 5 else None
            stats_message_id = user[6] if len(user) > 6 else None
            stats_channel_id = user[7] if len(user) > 7 else None
            
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


@update_stats_periodically.before_loop
async def before_update_stats():
    """Wait for the bot to be ready before starting the stats update loop."""
    await bot.wait_until_ready()


@update_stats_periodically.error
async def stats_error_handler(error):
    """Handle errors in the stats update task."""
    print(f"❌ Stats update task error: {error}")


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


@update_server_stats_periodically.before_loop
async def before_update_server_stats():
    """Wait for the bot to be ready before starting the server stats update loop."""
    await bot.wait_until_ready()

@update_server_stats_periodically.error
async def server_stats_error_handler(error):
    """Handle errors in the server stats update task."""
    print(f"❌ Server stats update task error: {error}")


@tasks.loop(seconds=60)
async def apex_play_monitor():
    """
    Monitor users' Steam status; when they start playing Apex (appid=1172470)
    record their RP. When they stop playing, send a DM summarizing RP change.
    """
    try:
        users = await db.get_all_users()
        for user in users:
            # Map fields safely (see update_stats_periodically)
            discord_id = user[0]
            apex_uid = user[2] if len(user) > 2 else None
            platform = user[3] if len(user) > 3 else None
            current_RP = user[4] if len(user) > 4 else None
            time_registered = user[5] if len(user) > 5 else None
            steam_id = user[8] if len(user) > 8 else None
            session_start_RP = user[9] if len(user) > 9 else None
            session_start_time = user[10] if len(user) > 10 else None
            is_in_game = bool(user[11]) if len(user) > 11 and user[11] is not None else False

            # Need a Steam ID to check game; skip otherwise
            if not steam_id:
                continue

            # Check current Steam game
            try:
                gameid = await get_player_game_async(steam_id)
            except Exception as e:
                print(f"❌ Failed to get Steam game for {steam_id}: {e}")
                continue

            # Normalize comparison
            if gameid is not None and str(gameid) == '1172470':
                # Player is in Apex
                if not is_in_game:
                    # Starting session; fetch current RP and record start
                    try:
                        player_data = await api.fetch_player_stats(apex_uid, platform)
                        rp = player_data['global']['rank']['rankScore']
                    except Exception as e:
                        print(f"❌ Failed to fetch RP for {apex_uid}: {e}")
                        continue

                    now = datetime.now(TIMEZONE_ET)
                    await db.set_session_start(discord_id, rp, now)
                    print(f"▶️ Recorded session start for {discord_id}: {rp} RP at {now}")
                else:
                    # already in-game; optionally update current_RP
                    pass
            else:
                # Player not in Apex. If they were in-game, end session and notify
                if is_in_game:
                    try:
                        player_data = await api.fetch_player_stats(apex_uid, platform)
                        final_rp = player_data['global']['rank']['rankScore']
                    except Exception as e:
                        print(f"❌ Failed to fetch final RP for {apex_uid}: {e}")
                        final_rp = current_RP if current_RP is not None else 0

                    now = datetime.now(TIMEZONE_ET)
                    # Compute delta
                    if session_start_RP is None:
                        delta = final_rp - (current_RP or 0)
                    else:
                        delta = final_rp - session_start_RP

                    # Update DB to end session
                    await db.set_session_end(discord_id, final_rp, now)

                    # Notify user via DM
                    try:
                        user_obj = await bot.fetch_user(discord_id)
                        duration = "unknown"
                        if session_start_time:
                            try:
                                # session_start_time stored as ISO or sqlite timestamp; display simple diff
                                duration_td = now - datetime.fromisoformat(session_start_time) if isinstance(session_start_time, str) else now - session_start_time
                                minutes = int(duration_td.total_seconds() // 60)
                                # Format duration: minutes -> "45 minutes" or hours/minutes -> "4h 3m"
                                if minutes < 60:
                                    minute_label = "minute" if minutes == 1 else "minutes"
                                    duration = f"{minutes} {minute_label}"
                                else:
                                    hours = minutes // 60
                                    mins = minutes % 60
                                    if mins:
                                        duration = f"{hours}h {mins}m"
                                    else:
                                        duration = f"{hours}h"
                            except Exception:
                                duration = "unknown"

                        # Format RP change with explicit sign (+/-)
                        sign_char = "+" if delta > 0 else "-" if delta < 0 else "+"
                        rp_str = f"{sign_char}{abs(int(delta))} RP"
                        await user_obj.send(f"``{rp_str} | {duration}``")
                        print(f"✉️ Sent session summary to {discord_id}: {delta} RP")
                    except Exception as e:
                        print(f"❌ Failed to send DM to {discord_id}: {e}")

    except Exception as e:
        print(f"❌ Error in apex_play_monitor: {e}")


@apex_play_monitor.before_loop
async def before_apex_play_monitor():
    await bot.wait_until_ready()


@apex_play_monitor.error
async def apex_play_monitor_error_handler(error):
    print(f"❌ Apex play monitor task error: {error}")


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

    if not thermal_throttle_alert.is_running():
        thermal_throttle_alert.start()
        print("✅ Started thermal throttle alert task")
    
    if not thermal_throttle_check.is_running():
        thermal_throttle_check.start()
        print("✅ Started thermal throttle check task")
    # Start Apex play monitoring task
    try:
        if not apex_play_monitor.is_running():
            apex_play_monitor.start()
            print("✅ Started Apex play monitoring task")
    except NameError:
        # If the task wasn't defined for some reason, ignore
        pass

    