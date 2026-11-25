"""
User-facing commands for the WayPoint Discord bot.
"""
import asyncio
import discord
from discord import app_commands
from datetime import datetime
from config import TIMEZONE_ET
from embeds import (
    create_history_embed,
    create_leaderboard_embed,
    create_maps_embed,
    create_player_stats_embed,
    create_session_summary_embed,
)
from utils import (
    format_duration_short,
    format_rp_per_hour,
    format_time_difference,
    parse_timestamp,
)
from api import get_steam_player_async


PLATFORM_CHOICES = [
    app_commands.Choice(name="PC (Origin / Steam)", value="PC"),
    app_commands.Choice(name="Xbox (X1)", value="X1"),
    app_commands.Choice(name="PlayStation (PS4/PS5)", value="PS4"),
]

# Module-level variables (will be set by setup)
bot = None
db = None
api = None


async def setup(bot_instance, db_instance, api_instance):
    """Register all user commands with the bot."""
    global bot, db, api
    bot = bot_instance
    db = db_instance
    api = api_instance

    bot.tree.add_command(register_user)
    bot.tree.add_command(unregister_user)
    bot.tree.add_command(profile)
    bot.tree.add_command(stats)
    bot.tree.add_command(lookup)
    bot.tree.add_command(maps)
    bot.tree.add_command(leaderboard)
    bot.tree.add_command(history)
    bot.tree.add_command(track)
    bot.tree.add_command(setsteam)
    bot.tree.add_command(getsteam)

    print("✅ User commands registered")


@app_commands.command(name="register", description="Register your Apex Legends account with the bot")
@app_commands.choices(platform=PLATFORM_CHOICES)
async def register_user(interaction: discord.Interaction, gamertag: str, platform: app_commands.Choice[str]):
    """Register a user with their Apex Legends gamertag and platform."""
    await interaction.response.defer(ephemeral=True)
    discord_id = interaction.user.id
    discord_server_id = interaction.guild.id
    plat = platform.value

    try:
        player_data = await api.fetch_player_stats_by_name(gamertag, plat)
        global_data = player_data.get('global', {})
        apex_uid = str(global_data.get('uid', ''))
        current_rp = int(global_data.get('rank', {}).get('rankScore', 0) or 0)
        if not apex_uid:
            raise ValueError("UID not returned by Apex API.")

        await db.save_user(discord_id, discord_server_id, apex_uid, plat, current_rp)
        await interaction.followup.send(
            f"✅ Registered **{global_data.get('name', gamertag)}** (UID `{apex_uid}`, platform `{plat}`, `{current_rp:,} RP`)!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to register: {e}", ephemeral=True)


@app_commands.command(name="unregister", description="Remove your registered Apex & Steam info from the bot")
async def unregister_user(interaction: discord.Interaction):
    """Remove the invoking user from the database."""
    deleted = await db.delete_user(interaction.user.id)
    if deleted:
        await interaction.response.send_message("✅ Your registration has been removed.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You are not currently registered.", ephemeral=True)


@app_commands.command(name="profile", description="View your linked Apex & Steam registration info")
async def profile(interaction: discord.Interaction):
    """Display the user's saved registration details."""
    user = await db.get_user(interaction.user.id)
    if user is None:
        await interaction.response.send_message("❌ You are not registered. Use `/register` first.", ephemeral=True)
        return

    apex_uid = user[2]
    platform = user[3]
    current_rp = user[4]
    time_registered = user[5]
    steam_id = user[8] if len(user) > 8 else None
    is_in_game = bool(user[11]) if len(user) > 11 and user[11] is not None else False

    embed = discord.Embed(title=f"🪪 Profile — {interaction.user.display_name}", colour=discord.Colour.blurple())
    embed.add_field(name="Apex UID", value=f"`{apex_uid}`", inline=True)
    embed.add_field(name="Platform", value=f"`{platform}`", inline=True)
    embed.add_field(name="Last Recorded RP", value=f"`{current_rp if current_rp is not None else 'N/A'}`", inline=True)
    embed.add_field(name="Steam ID", value=f"`{steam_id or 'Not linked'}`", inline=True)
    embed.add_field(name="Manual /track", value="🟢 Active" if time_registered else "⚪ Inactive", inline=True)
    embed.add_field(name="Steam Auto-Track", value="🟢 In Apex" if is_in_game else "⚪ Idle", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="stats", description="Show auto-updating Apex stats (or check a friend's stats)")
async def stats(interaction: discord.Interaction, player: discord.Member = None):
    """Display player statistics in an auto-updating embed, or check a friend's stats."""
    target_user = player or interaction.user
    checking_other = player is not None and player.id != interaction.user.id

    user = await db.get_user(target_user.id)
    if user is None:
        msg = (
            f"❌ {target_user.display_name} is not registered yet."
            if checking_other
            else "❌ You are not registered. Please use `/register` first."
        )
        await interaction.response.send_message(msg, ephemeral=True)
        return

    apex_uid = user[2] if len(user) > 2 else None
    platform = user[3] if len(user) > 3 else None
    stats_message_id = user[6] if len(user) > 6 else None

    if checking_other:
        await interaction.response.defer(ephemeral=True)
    else:
        await interaction.response.send_message("🔄 Updating your stats...", ephemeral=True, delete_after=2)

    await api.fetch_all_data()
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")

    try:
        stats_embed = await create_player_stats_embed(platform, apex_uid, formatted_time, api)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to create stats embed: {e}", ephemeral=True)
        return

    if checking_other:
        await interaction.followup.send(embed=stats_embed, ephemeral=True)
        return

    stats_channel = interaction.channel
    try:
        if stats_message_id:
            try:
                stats_message = await stats_channel.fetch_message(stats_message_id)
                await stats_message.edit(embed=stats_embed)
            except discord.NotFound:
                stats_message = await stats_channel.send(embed=stats_embed)
        else:
            stats_message = await stats_channel.send(embed=stats_embed)

        await db.update_user_stats_message(target_user.id, stats_message.id, stats_channel.id)
    except discord.Forbidden:
        await interaction.followup.send("❌ Bot lacks permissions to send messages in this channel.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Failed to send stats message: {e}", ephemeral=True)


@app_commands.command(name="lookup", description="Look up any Apex player's current ranked stats without registering")
@app_commands.choices(platform=PLATFORM_CHOICES)
async def lookup(interaction: discord.Interaction, gamertag: str, platform: app_commands.Choice[str]):
    """Look up any Apex player by gamertag and platform."""
    await interaction.response.defer()
    await api.fetch_all_data()
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")

    try:
        player_data = await api.fetch_player_stats_by_name(gamertag, platform.value)
        apex_uid = str(player_data.get('global', {}).get('uid', ''))
        embed = await create_player_stats_embed(
            platform.value, apex_uid, formatted_time, api, player_data=player_data
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Could not find stats for `{gamertag}` ({platform.value}): {e}", ephemeral=True)


@app_commands.command(name="maps", description="Show current and upcoming Apex Legends map rotations")
async def maps(interaction: discord.Interaction):
    """Display current and next Ranked, Pubs, and LTM maps."""
    await interaction.response.defer()
    await api.fetch_all_data()
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    embed = create_maps_embed(api, formatted_time)
    await interaction.followup.send(embed=embed)


@app_commands.command(name="leaderboard", description="Show the server's Apex Legends RP leaderboard")
async def leaderboard(interaction: discord.Interaction):
    """Fetch live RP for all registered users in this server and display a leaderboard."""
    await interaction.response.defer()
    users = await db.get_server_users(interaction.guild.id)

    if not users:
        now_et = datetime.now(TIMEZONE_ET)
        embed = create_leaderboard_embed(interaction.guild.name, [], now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0"))
        await interaction.followup.send(embed=embed)
        return

    async def _fetch_entry(user_row):
        discord_id = user_row[0]
        apex_uid = user_row[2]
        platform = user_row[3]
        member = interaction.guild.get_member(discord_id)
        display_name = member.display_name if member else f"User {discord_id}"
        try:
            data = await api.fetch_player_stats(apex_uid, platform)
            global_data = data.get('global', {})
            rank_data = global_data.get('rank', {})
            rp = int(rank_data.get('rankScore', 0) or 0)
            rank_label = f"{rank_data.get('rankName', 'Unranked')} {rank_data.get('rankDiv', '')}".strip()
            apex_name = global_data.get('name', 'Unknown')
        except Exception:
            rp = int(user_row[4] or 0)
            rank_label = "Cached"
            apex_name = str(apex_uid)

        return {
            "display_name": display_name,
            "apex_name": apex_name,
            "platform": platform,
            "rank_label": rank_label,
            "rp": rp,
        }

    entries = await asyncio.gather(*[_fetch_entry(u) for u in users])
    entries.sort(key=lambda e: e["rp"], reverse=True)

    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    embed = create_leaderboard_embed(interaction.guild.name, entries, formatted_time)
    await interaction.followup.send(embed=embed)


@app_commands.command(name="history", description="View your (or a friend's) recent RP session history")
async def history(interaction: discord.Interaction, player: discord.Member = None):
    """Display recent completed RP sessions and lifetime net RP."""
    target = player or interaction.user
    user = await db.get_user(target.id)
    if user is None:
        await interaction.response.send_message(
            f"❌ {target.display_name} is not registered yet.",
            ephemeral=True
        )
        return

    sessions = await db.get_user_sessions(target.id, limit=8)
    totals = await db.get_user_session_totals(target.id)
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    embed = create_history_embed(target.display_name, sessions, totals, formatted_time)
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="track", description="Toggle tracking your Apex RP (start/stop)")
async def track(interaction: discord.Interaction):
    """Toggle manual RP tracking for the calling user."""
    await interaction.response.defer(ephemeral=True)
    discord_id = interaction.user.id
    user = await db.get_user(discord_id)

    if user is None:
        await interaction.followup.send(
            "❌ You are not registered. Please use `/register` first.",
            ephemeral=True,
        )
        return

    discord_server_id = user[1] if len(user) > 1 else interaction.guild.id
    apex_uid = user[2] if len(user) > 2 else None
    platform = user[3] if len(user) > 3 else None
    current_RP = user[4] if len(user) > 4 else None
    time_registered = user[5] if len(user) > 5 else None

    try:
        player_data = await api.fetch_player_stats(apex_uid, platform)
        rank_data = player_data["global"]["rank"]
        apex_rp = int(rank_data["rankScore"])
        rank_label = f"{rank_data.get('rankName', '')} {rank_data.get('rankDiv', '')}".strip() or None
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to fetch RP from API: {e}", ephemeral=True)
        return

    if time_registered:
        try:
            start_time = parse_timestamp(time_registered, TIMEZONE_ET)
            if start_time is None:
                raise ValueError("Invalid timestamp")
        except ValueError:
            await db.update_user_tracking(discord_id, apex_rp, None)
            await interaction.followup.send(
                "❌ Tracking start time in DB was invalid and has been reset. Run `/track` again to start a new session.",
                ephemeral=True,
            )
            return

        end_time = datetime.now(TIMEZONE_ET)
        start_rp = current_RP if current_RP is not None else apex_rp
        rp_change = apex_rp - start_rp
        time_played = format_time_difference(start_time, end_time)
        duration_short = format_duration_short(start_time, end_time)
        avg_rp_per_hour = format_rp_per_hour(rp_change, start_time, end_time)

        await db.update_user_tracking(discord_id, apex_rp, None)
        await db.record_session(
            discord_id, discord_server_id, start_rp, apex_rp, start_time, end_time, source="manual"
        )

        summary_embed = create_session_summary_embed(
            player_name=interaction.user.display_name,
            start_rp=start_rp,
            end_rp=apex_rp,
            duration_str=duration_short,
            rp_per_hour_str=avg_rp_per_hour,
            rank_label=rank_label,
            source="manual",
        )

        # Post to server sessions feed if configured and RP changed
        if rp_change != 0 and interaction.guild:
            server = await db.get_server(interaction.guild.id)
            sessions_channel_id = server[3] if server and len(server) > 3 else None
            if sessions_channel_id:
                feed_channel = bot.get_channel(sessions_channel_id)
                if feed_channel:
                    try:
                        await feed_channel.send(embed=summary_embed)
                    except Exception as e:
                        print(f"❌ Failed to post manual session to channel {sessions_channel_id}: {e}")

        await interaction.followup.send(
            content=f"✅ Tracking ended ({time_played}).",
            embed=summary_embed,
            ephemeral=True,
        )
        return

    await db.update_user_tracking(discord_id, apex_rp, datetime.now(TIMEZONE_ET))
    await interaction.followup.send(f"✅ Tracking started — current RP: `{apex_rp:,}`", ephemeral=True)


@app_commands.command(name="getsteam", description="Show your saved Steam profile (ephemeral)")
async def getsteam(interaction: discord.Interaction):
    """Display the invoking user's saved Steam info."""
    user = await db.get_user(interaction.user.id)
    if user is None:
        await interaction.response.send_message("❌ You are not registered. Use `/register` first.", ephemeral=True)
        return

    steam_id = user[8] if len(user) > 8 else None
    if not steam_id:
        await interaction.response.send_message("❌ No Steam ID saved. Set one with `/setsteam`.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    player = await get_steam_player_async(steam_id)

    if player is None:
        await interaction.followup.send(
            f"⚠️ Steam ID `{steam_id}` saved, but the profile could not be fetched (it may be private).",
            ephemeral=True,
        )
        return

    persona = player.get('personaname', 'Unknown')
    avatar = player.get('avatarfull') or player.get('avatar')
    profile_url = f"https://steamcommunity.com/profiles/{player.get('steamid')}"

    embed = discord.Embed(
        title=f"Steam: {persona}",
        description=f"ID: `{player.get('steamid')}`\n[Profile]({profile_url})",
        color=discord.Colour.blue(),
    )
    if avatar:
        embed.set_thumbnail(url=avatar)

    await interaction.followup.send(embed=embed, ephemeral=True)


@app_commands.command(name="setsteam", description="Register your SteamID64 or vanity name for automatic Apex monitoring")
async def setsteam(interaction: discord.Interaction, steamid: str):
    """Save the invoking user's SteamID64 to the database for Apex play monitoring."""
    await interaction.response.defer(ephemeral=True)
    discord_id = interaction.user.id

    user = await db.get_user(discord_id)
    if user is None:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.", ephemeral=True)
        return

    player = await get_steam_player_async(steamid)
    if player is None:
        await interaction.followup.send(
            "❌ Could not validate that Steam ID/vanity exists. Please provide a valid SteamID64 or vanity name.",
            ephemeral=True,
        )
        return

    resolved_steamid = player.get('steamid')
    persona = player.get('personaname')

    try:
        success = await db.update_user_steam_id(discord_id, resolved_steamid)
        if success:
            await interaction.followup.send(f"✅ Saved Steam ID `{resolved_steamid}` for `{persona}`.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to save Steam ID (user not found in database).", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to save Steam ID: {e}", ephemeral=True)
