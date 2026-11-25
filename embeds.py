"""
Discord embed creation functions for the WayPoint Discord bot.
"""
import discord
from config import RANK_THRESHOLDS, TIMEZONE_ET
from utils import format_duration_short, parse_timestamp


def _get_rank_color(rank_name: str) -> discord.Colour:
    """Map an Apex rank tier name to a Discord embed color."""
    rank_lower = (rank_name or "").lower()
    if "predator" in rank_lower:
        return discord.Colour.red()
    if "master" in rank_lower:
        return discord.Colour.purple()
    if "diamond" in rank_lower:
        return discord.Colour.blue()
    if "platinum" in rank_lower:
        return discord.Colour.teal()
    if "gold" in rank_lower:
        return discord.Colour.gold()
    if "silver" in rank_lower:
        return discord.Colour.light_grey()
    if "bronze" in rank_lower:
        return discord.Colour.dark_grey()
    return discord.Colour.default()


def _get_next_rank_info(rank_score: int, predcap_value: int) -> tuple[int, str]:
    """Return (rp_until_next_rank, next_rank_name) for a given RP score."""
    if rank_score >= 16000:
        rp_until_pred = max(0, predcap_value - rank_score) if predcap_value else 0
        return rp_until_pred, "Predator"

    for idx, (threshold, tier_name) in enumerate(RANK_THRESHOLDS):
        if rank_score >= threshold:
            next_threshold, next_name = RANK_THRESHOLDS[idx - 1]
            return max(0, next_threshold - rank_score), next_name

    # Below Bronze
    lowest_threshold, lowest_name = RANK_THRESHOLDS[-1]
    return max(0, lowest_threshold - rank_score), lowest_name


async def create_player_stats_embed(platform, apex_uid, formatted_time, api, player_data=None):
    """
    Create a Discord embed with player statistics.

    Args:
        platform (str): Gaming platform (PC, PS4, X1)
        apex_uid (str): Apex Legends UID
        formatted_time (str): Formatted timestamp string
        api (API): API instance with cached data
        player_data (dict, optional): Pre-fetched player payload to avoid duplicate API calls

    Returns:
        discord.Embed: Player statistics embed
    """
    if player_data is None:
        player_data = await api.fetch_player_stats(apex_uid, platform)

    global_data = player_data.get('global', {})
    ranked_data = global_data.get('rank', {})

    rank_name = ranked_data.get('rankName', 'Unranked')
    rank_div = ranked_data.get('rankDiv', '')
    rank_score = int(ranked_data.get('rankScore', 0) or 0)

    predcap_value = api.get_predcap_value(platform)
    rp_until_pred = max(0, predcap_value - rank_score) if predcap_value else 0
    rp_until_next_rank, next_rank_name = _get_next_rank_info(rank_score, predcap_value)

    colour = _get_rank_color(rank_name)
    player_name = global_data.get('name', 'Unknown')
    player_uid = global_data.get('uid', apex_uid or 'Unknown')

    player_embed = discord.Embed(
        title="🎮 **__APEX LEGENDS STATS__**",
        description=f"**Player:** `{player_name}`\n**UID:** `{player_uid}`",
        colour=colour
    )

    # Ranked Stats Section
    player_embed.add_field(name="📊 **__RANKED STATS__**", value="", inline=False)
    rank_label = f"{rank_name} {rank_div}".strip()
    player_embed.add_field(name="🏆 Current Rank", value=f"```{rank_label}```", inline=True)
    player_embed.add_field(name="🌟 Rank Points", value=f"```{rank_score} RP```", inline=True)
    player_embed.add_field(name=f"🎯 RP to {next_rank_name}", value=f"```{rp_until_next_rank} RP```", inline=True)

    # Map & Mode Info Section (safe .get() lookups)
    ltm_current = api.ltm_data.get('current', {}) if isinstance(api.ltm_data, dict) else {}
    ltm_next = api.ltm_data.get('next', {}) if isinstance(api.ltm_data, dict) else {}
    ranked_map = api.map_data.get('ranked', {}) if isinstance(api.map_data, dict) else {}
    ranked_current = ranked_map.get('current', {}) if isinstance(ranked_map, dict) else {}
    ranked_next = ranked_map.get('next', {}) if isinstance(ranked_map, dict) else {}

    ranked_mins = ranked_current.get('remainingMins')
    ranked_time_str = f"{round(ranked_mins / 60, 1)}h" if isinstance(ranked_mins, (int, float)) else "N/A"
    ltm_mins = ltm_current.get('remainingMins')
    ltm_time_str = f"{ltm_mins}m" if ltm_mins is not None else "N/A"

    player_embed.add_field(name="🗺️ **__MAP ROTATION__**", value="", inline=False)
    player_embed.add_field(name="LTM", value=f"```{ltm_current.get('eventName', 'N/A')}```", inline=True)
    player_embed.add_field(name="⏱️ Time Remaining", value=f"```{ltm_time_str}```", inline=True)
    player_embed.add_field(name="Next LTM", value=f"```{ltm_next.get('eventName', 'N/A')}```", inline=True)
    player_embed.add_field(name="Ranked Map", value=f"```{ranked_current.get('map', 'N/A')}```", inline=True)
    player_embed.add_field(name="⏰ Time Remaining", value=f"```{ranked_time_str}```", inline=True)
    player_embed.add_field(name="Next Map", value=f"```{ranked_next.get('map', 'N/A')}```", inline=True)

    # Pred Info Section
    player_embed.add_field(name="📈 **__PRED INFO__**", value="", inline=False)
    player_embed.add_field(name="🏆 Predator Cap", value=f"```{predcap_value} RP```", inline=True)
    player_embed.add_field(name="🎯 RP to Predator", value=f"```{rp_until_pred} RP```", inline=True)
    player_embed.add_field(name="🌍 Platform", value=f"```{platform}```", inline=True)

    player_embed.set_footer(text=f"last updated {formatted_time} ET")

    rank_img_url = ranked_data.get('rankImg')
    if rank_img_url:
        player_embed.set_thumbnail(url=rank_img_url)
        player_embed.set_author(name=f"{player_name}'s Profile", icon_url=rank_img_url)
    else:
        player_embed.set_author(name=f"{player_name}'s Profile")

    return player_embed


def create_maps_embed(api, formatted_time) -> discord.Embed:
    """Create a focused Discord embed for current & upcoming Apex map rotations."""
    map_data = api.map_data if isinstance(api.map_data, dict) else {}
    ltm_data = api.ltm_data if isinstance(api.ltm_data, dict) else {}

    ranked = map_data.get('ranked', {})
    battle_royale = map_data.get('battle_royale', {})

    embed = discord.Embed(
        title="🗺️ **APEX LEGENDS MAP ROTATION**",
        description="Current and upcoming maps across modes",
        colour=discord.Colour.teal()
    )

    for label, section in [("🏆 Ranked", ranked), ("🎯 Pubs (BR)", battle_royale)]:
        curr = section.get('current', {}) if isinstance(section, dict) else {}
        nxt = section.get('next', {}) if isinstance(section, dict) else {}
        mins = curr.get('remainingMins')
        rem = f"{round(mins / 60, 1)}h ({mins}m)" if isinstance(mins, (int, float)) else "N/A"
        embed.add_field(
            name=label,
            value=f"**Current:** `{curr.get('map', 'N/A')}`\n**Remaining:** `{rem}`\n**Next:** `{nxt.get('map', 'N/A')}`",
            inline=True
        )

    ltm_curr = ltm_data.get('current', {})
    ltm_nxt = ltm_data.get('next', {})
    ltm_mins = ltm_curr.get('remainingMins')
    ltm_rem = f"{ltm_mins}m" if ltm_mins is not None else "N/A"
    ltm_map_suffix = f" on `{ltm_curr.get('map')}`" if ltm_curr.get('map') else ""
    embed.add_field(
        name="⚡ LTM / Mixtape",
        value=f"**Current:** `{ltm_curr.get('eventName', 'N/A')}`{ltm_map_suffix}\n**Remaining:** `{ltm_rem}`\n**Next:** `{ltm_nxt.get('eventName', 'N/A')}`",
        inline=False
    )

    embed.set_footer(text=f"last updated {formatted_time} ET")
    return embed


def create_leaderboard_embed(guild_name: str, entries: list[dict], formatted_time: str) -> discord.Embed:
    """
    Create a server RP leaderboard embed.

    Each entry dict expects: display_name, apex_name, platform, rank_label, rp.
    """
    embed = discord.Embed(
        title=f"🏅 **{guild_name} — Apex RP Leaderboard**",
        colour=discord.Colour.gold()
    )

    if not entries:
        embed.description = "No registered players found in this server yet. Use `/register` to join!"
        embed.set_footer(text=f"last updated {formatted_time} ET")
        return embed

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for idx, entry in enumerate(entries, start=1):
        prefix = medals.get(idx, f"`#{idx}`")
        lines.append(
            f"{prefix} **{entry['display_name']}** (`{entry['apex_name']}` · {entry['platform']})\n"
            f"   └ `{entry['rank_label']}` — **{entry['rp']:,} RP**"
        )

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"last updated {formatted_time} ET")
    return embed


def create_session_summary_embed(
    player_name: str,
    start_rp: int,
    end_rp: int,
    duration_str: str,
    rp_per_hour_str: str,
    rank_label: str | None = None,
    source: str = "steam",
) -> discord.Embed:
    """Create a rich embed summarizing a completed RP session."""
    delta = end_rp - start_rp
    if delta > 0:
        colour = discord.Colour.green()
        delta_str = f"+{delta:,} RP"
        emoji = "📈"
    elif delta < 0:
        colour = discord.Colour.red()
        delta_str = f"{delta:,} RP"
        emoji = "📉"
    else:
        colour = discord.Colour.light_grey()
        delta_str = "0 RP"
        emoji = "➖"

    source_label = "Auto (Steam)" if source == "steam" else "Manual (/track)"
    embed = discord.Embed(
        title=f"{emoji} **Ranked Session Complete — {player_name}**",
        colour=colour
    )
    embed.add_field(name="RP Change", value=f"```{delta_str}```", inline=True)
    embed.add_field(name="Duration", value=f"```{duration_str}```", inline=True)
    embed.add_field(name="Rate", value=f"```{rp_per_hour_str}```", inline=True)
    embed.add_field(name="Start → End RP", value=f"```{start_rp:,} → {end_rp:,}```", inline=True)
    if rank_label:
        embed.add_field(name="Current Rank", value=f"```{rank_label}```", inline=True)
    embed.set_footer(text=f"Tracked via {source_label}")
    return embed


def create_history_embed(display_name: str, sessions: list, totals: tuple, formatted_time: str) -> discord.Embed:
    """Create an embed showing a player's recent RP sessions and lifetime totals."""
    count, total_rp, best_rp, worst_rp = totals
    embed = discord.Embed(
        title=f"📜 **RP Session History — {display_name}**",
        colour=discord.Colour.blue()
    )

    if count == 0:
        embed.description = "No completed sessions recorded yet. Use `/track` or link Steam with `/setsteam`!"
        embed.set_footer(text=f"last updated {formatted_time} ET")
        return embed

    embed.add_field(name="Sessions", value=f"```{count}```", inline=True)
    embed.add_field(name="Net RP", value=f"```{total_rp:+,} RP```", inline=True)
    embed.add_field(name="Best / Worst", value=f"```{best_rp:+,} / {worst_rp:+,}```", inline=True)

    lines = []
    for start_rp, end_rp, rp_change, started_at, ended_at, source in sessions:
        start_dt = parse_timestamp(started_at, TIMEZONE_ET)
        end_dt = parse_timestamp(ended_at, TIMEZONE_ET)
        dur = format_duration_short(start_dt, end_dt) if start_dt and end_dt else "?"
        date_str = end_dt.strftime("%m/%d %I:%M %p").lstrip("0") if end_dt else ""
        tag = "Steam" if source == "steam" else "Manual"
        lines.append(f"`{rp_change:+,} RP` ({start_rp:,} → {end_rp:,}) · {dur} · {tag} · {date_str}")

    embed.add_field(name="Recent Sessions", value="\n".join(lines), inline=False)
    embed.set_footer(text=f"last updated {formatted_time} ET")
    return embed


def create_server_status_embed(formatted_time, api):
    """
    Create a Discord embed with server status information.

    Args:
        formatted_time (str): Formatted timestamp string
        api (API): API instance with cached data

    Returns:
        discord.Embed: Server status embed
    """
    status_emojis = {
        "UP": "🟢",
        "DOWN": "🔴",
        "SLOW": "🟡",
        "UNKNOWN": "⚪"
    }

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

    def _add_server_section(title: str, data_dict: dict, include_flags: bool):
        server_embed.add_field(name=title, value="", inline=False)
        if not isinstance(data_dict, dict) or not data_dict:
            server_embed.add_field(name="Status", value="```⚪ UNAVAILABLE```", inline=True)
            return
        for key, data in data_dict.items():
            status = str(data.get('Status', 'UNKNOWN')).upper() if isinstance(data, dict) else "UNKNOWN"
            emoji = status_emojis.get(status, "⚪")
            name = f"{region_flags.get(key.upper(), '❓')} {key}" if include_flags else f"{key}"
            server_embed.add_field(name=name, value=f"```{emoji} {status}```", inline=True)

    _add_server_section("🛠️ **___MATCHMAKING SERVERS___**", api.matchmaking_server_data, True)
    _add_server_section("🔗 **___CROSSPLAY SERVERS___**", api.crossplay_server_data, True)
    _add_server_section("🎮 **___CONSOLE SERVERS___**", api.console_server_data, False)

    server_embed.set_footer(text=f"last updated {formatted_time} ET")
    server_embed.set_thumbnail(
        url="https://upload.wikimedia.org/wikipedia/commons/b/b1/Apex_legends_simple_logo.jpg"
    )

    return server_embed
