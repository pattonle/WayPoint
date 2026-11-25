"""
Periodic tasks for the WayPoint Discord bot using discord.ext.tasks.
"""
import discord
from discord.ext import tasks
from datetime import datetime, time
from config import OWNER_DISCORD_ID, TIMEZONE_ET
from embeds import (
    create_player_stats_embed,
    create_server_status_embed,
    create_session_summary_embed,
)
from utils import (
    check_cpu_temp,
    format_duration_short,
    format_rp_per_hour,
    parse_timestamp,
)


# Global references (will be set by setup_tasks)
bot = None
db = None
api = None


@tasks.loop(time=time(hour=9, minute=0, tzinfo=TIMEZONE_ET))
async def thermal_throttle_check():
    """Send daily Raspberry Pi CPU temperature check to the bot owner."""
    if not OWNER_DISCORD_ID:
        return
    cpu_temp = check_cpu_temp()
    if cpu_temp is not None:
        user = await bot.fetch_user(OWNER_DISCORD_ID)
        await user.send(f"🤖 Daily CPU Temperature: {cpu_temp.temperature:.1f}°C")


@thermal_throttle_check.before_loop
async def before_thermal_throttle_check():
    await bot.wait_until_ready()


@thermal_throttle_check.error
async def thermal_throttle_check_error_handler(error):
    """Handle errors in the thermal throttle check task."""
    print(f"❌ Thermal throttle check task error: {error}")


@tasks.loop(minutes=10)
async def thermal_throttle_alert():
    """Alert the bot owner if Raspberry Pi CPU temperature is elevated."""
    if not OWNER_DISCORD_ID:
        return
    cpu_temp = check_cpu_temp()
    if cpu_temp is not None:
        user = await bot.fetch_user(OWNER_DISCORD_ID)
        if cpu_temp.temperature >= 80:
            await user.send(f"🚩 URGENT Warning: CPU temperature is at {cpu_temp.temperature:.1f}°C.")
        elif cpu_temp.temperature > 70:
            await user.send(f"⚠️ Critical Warning: CPU temperature is at {cpu_temp.temperature:.1f}°C.")
        elif cpu_temp.temperature >= 65:
            await user.send(f"🚩 Pi is running hotter than usual. CPU temperature is at {cpu_temp.temperature:.1f}°C.")


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
        await api.fetch_all_data()
        users = await db.get_all_users()

        for user in users:
            discord_id = user[0]
            apex_uid = user[2] if len(user) > 2 else None
            platform = user[3] if len(user) > 3 else None
            stats_message_id = user[6] if len(user) > 6 else None
            stats_channel_id = user[7] if len(user) > 7 else None

            if not stats_message_id or not stats_channel_id:
                continue

            channel = bot.get_channel(stats_channel_id)
            if channel is None:
                print(f"❌ Could not find channel ID {stats_channel_id} for user {discord_id}")
                continue

            try:
                message = await channel.fetch_message(stats_message_id)
            except discord.NotFound:
                print(f"❌ Could not find message ID {stats_message_id} in channel ID {stats_channel_id} for user {discord_id}")
                continue

            now_et = datetime.now(TIMEZONE_ET)
            formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")

            try:
                updated_embed = await create_player_stats_embed(platform, apex_uid, formatted_time, api)
            except Exception as e:
                print(f"❌ Failed to create stats embed for user {discord_id}: {e}")
                continue

            try:
                await message.edit(embed=updated_embed)
            except discord.Forbidden:
                print(f"❌ Bot lacks permissions to edit message ID {stats_message_id} in channel ID {stats_channel_id} for user {discord_id}")
            except discord.HTTPException as e:
                print(f"❌ Failed to edit stats message for user {discord_id}: {e}")

    except Exception as e:
        print(f"❌ Error in update_stats_periodically: {e}")


@update_stats_periodically.before_loop
async def before_update_stats():
    await bot.wait_until_ready()


@update_stats_periodically.error
async def stats_error_handler(error):
    print(f"❌ Stats update task error: {error}")


@tasks.loop(minutes=5)
async def update_server_stats_periodically():
    """Update server status embeds every 5 minutes."""
    try:
        await api.fetch_all_data()
        servers = await db.get_all_servers()

        for server in servers:
            discord_server_id = server[0]
            apex_server_channel_id = server[1] if len(server) > 1 else None
            apex_server_message_id = server[2] if len(server) > 2 else None

            if not apex_server_channel_id or not apex_server_message_id:
                continue

            channel = bot.get_channel(apex_server_channel_id)
            if channel is None:
                print(f"❌ Could not find channel ID {apex_server_channel_id} for server {discord_server_id}")
                continue

            try:
                message = await channel.fetch_message(apex_server_message_id)
            except discord.NotFound:
                print(f"❌ Could not find message ID {apex_server_message_id} in channel ID {apex_server_channel_id} for server {discord_server_id}")
                continue

            now_et = datetime.now(TIMEZONE_ET)
            formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
            updated_embed = create_server_status_embed(formatted_time, api)

            try:
                await message.edit(embed=updated_embed)
            except discord.Forbidden:
                print(f"❌ Bot lacks permissions to edit message ID {apex_server_message_id} in channel ID {apex_server_channel_id} for server {discord_server_id}")
            except discord.HTTPException as e:
                print(f"❌ Failed to edit server status message for server {discord_server_id}: {e}")

    except Exception as e:
        print(f"❌ Error in update_server_stats_periodically: {e}")


@update_server_stats_periodically.before_loop
async def before_update_server_stats():
    await bot.wait_until_ready()


@update_server_stats_periodically.error
async def server_stats_error_handler(error):
    print(f"❌ Server stats update task error: {error}")


@tasks.loop(seconds=60)
async def apex_play_monitor():
    """
    Monitor users' Steam status; when they start playing Apex (appid=1172470),
    record their RP. When they stop playing, record the session and notify.
    """
    try:
        users = await db.get_all_users()
        for user in users:
            discord_id = user[0]
            discord_server_id = user[1] if len(user) > 1 else None
            apex_uid = user[2] if len(user) > 2 else None
            platform = user[3] if len(user) > 3 else None
            current_RP = user[4] if len(user) > 4 else None
            steam_id = user[8] if len(user) > 8 else None
            session_start_RP = user[9] if len(user) > 9 else None
            session_start_time = user[10] if len(user) > 10 else None
            is_in_game = bool(user[11]) if len(user) > 11 and user[11] is not None else False

            if not steam_id:
                continue

            try:
                gameid = await api.get_player_game(steam_id)
            except Exception as e:
                print(f"❌ Failed to get Steam game for {steam_id}: {e}")
                continue

            if gameid is not None and str(gameid) == '1172470':
                if not is_in_game:
                    try:
                        player_data = await api.fetch_player_stats(apex_uid, platform)
                        rp = int(player_data['global']['rank']['rankScore'])
                    except Exception as e:
                        print(f"❌ Failed to fetch RP for {apex_uid}: {e}")
                        continue

                    now = datetime.now(TIMEZONE_ET)
                    await db.set_session_start(discord_id, rp, now)
                    print(f"▶️ Recorded session start for {discord_id}: {rp} RP at {now}")
            elif is_in_game:
                rank_label = None
                player_name = str(discord_id)
                try:
                    player_data = await api.fetch_player_stats(apex_uid, platform)
                    global_data = player_data.get('global', {})
                    rank_data = global_data.get('rank', {})
                    final_rp = int(rank_data.get('rankScore', 0))
                    player_name = global_data.get('name', player_name)
                    rank_label = f"{rank_data.get('rankName', '')} {rank_data.get('rankDiv', '')}".strip() or None
                except Exception as e:
                    print(f"❌ Failed to fetch final RP for {apex_uid}: {e}")
                    final_rp = current_RP if current_RP is not None else 0

                now = datetime.now(TIMEZONE_ET)
                start_rp = session_start_RP if session_start_RP is not None else (current_RP or 0)
                delta = final_rp - start_rp

                await db.set_session_end(discord_id, final_rp)

                if delta == 0:
                    print(f"ℹ️ No RP change for {discord_id}; skipping notification")
                    continue

                start_dt = parse_timestamp(session_start_time, TIMEZONE_ET) or now
                await db.record_session(
                    discord_id,
                    discord_server_id,
                    start_rp,
                    final_rp,
                    start_dt,
                    now,
                    source="steam",
                )

                duration_str = format_duration_short(start_dt, now)
                rp_hr_str = format_rp_per_hour(delta, start_dt, now)

                try:
                    user_obj = await bot.fetch_user(discord_id)
                    display_name = user_obj.display_name
                except Exception:
                    user_obj = None
                    display_name = player_name

                summary_embed = create_session_summary_embed(
                    player_name=display_name,
                    start_rp=start_rp,
                    end_rp=final_rp,
                    duration_str=duration_str,
                    rp_per_hour_str=rp_hr_str,
                    rank_label=rank_label,
                    source="steam",
                )

                # Post to server sessions feed if configured
                if discord_server_id:
                    server = await db.get_server(discord_server_id)
                    sessions_channel_id = server[3] if server and len(server) > 3 else None
                    if sessions_channel_id:
                        feed_channel = bot.get_channel(sessions_channel_id)
                        if feed_channel:
                            try:
                                await feed_channel.send(embed=summary_embed)
                            except Exception as e:
                                print(f"❌ Failed to post session to channel {sessions_channel_id}: {e}")

                # Also DM the player
                if user_obj:
                    try:
                        await user_obj.send(embed=summary_embed)
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
    """Initialize and start all periodic tasks."""
    global bot, db, api
    bot = bot_instance
    db = db_instance
    api = api_instance

    if not update_stats_periodically.is_running():
        update_stats_periodically.start()
        print("✅ Started stats update task")

    if not update_server_stats_periodically.is_running():
        update_server_stats_periodically.start()
        print("✅ Started server stats update task")

    if OWNER_DISCORD_ID:
        if not thermal_throttle_alert.is_running():
            thermal_throttle_alert.start()
            print("✅ Started thermal throttle alert task")
        if not thermal_throttle_check.is_running():
            thermal_throttle_check.start()
            print("✅ Started thermal throttle check task")

    if not apex_play_monitor.is_running():
        apex_play_monitor.start()
        print("✅ Started Apex play monitoring task")
