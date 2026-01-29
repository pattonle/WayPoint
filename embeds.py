"""
Discord embed creation functions for the WayPoint Discord bot.
"""
import discord


async def create_player_stats_embed(platform, apex_uid, formatted_time, api):
    """
    Create a Discord embed with player statistics.
    
    Args:
        platform (str): Gaming platform (PC, PS4, X1)
        apex_uid (str): Apex Legends UID
        formatted_time (str): Formatted timestamp string
        api (API): API instance with cached data
        
    Returns:
        discord.Embed: Player statistics embed
    """
    # Fetch player data
    player_data = await api.fetch_player_stats(apex_uid, platform)
    global_data = player_data['global']
    ranked_data = global_data['rank']
    
    # Get predcap value
    predcap_value = api.get_predcap_value(platform)
    
    # Determine embed color based on rank
    rank_name_lower = ranked_data['rankName'].lower()
    if "predator" in rank_name_lower:
        colour = discord.Colour.gold()
    elif "master" in rank_name_lower:
        colour = discord.Colour.purple()
    elif "diamond" in rank_name_lower:
        colour = discord.Colour.blue()
    elif "platinum" in rank_name_lower:
        colour = discord.Colour.teal()
    elif "gold" in rank_name_lower:
        colour = discord.Colour.green()
    elif "silver" in rank_name_lower:
        colour = discord.Colour.light_grey()
    elif "bronze" in rank_name_lower:
        colour = discord.Colour.dark_grey()
    else:
        colour = discord.Colour.default()
    
    # Create embed
    player_embed = discord.Embed(
        title=f"🎮 **__APEX LEGENDS STATS__**",
        description=f"**Player:** `{global_data['name']}`\n**UID:** `{global_data['uid']}`",
        colour=colour
    )
    
    # Ranked Stats Section
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
    
    # Calculate RP to Predator
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
        value=f"```{api.ltm_data['current']['eventName']}```",
        inline=True
    )
    
    player_embed.add_field(
        name="⏱️ Time Remaining",
        value=f"```{api.ltm_data['current']['remainingMins']}m```",
        inline=True
    )
    
    player_embed.add_field(
        name="Next LTM",
        value=f"```{api.ltm_data['next']['eventName']}```",
        inline=True
    )
    
    player_embed.add_field(
        name="Ranked Map",
        value=f"```{api.map_data['ranked']['current']['map']}```",
        inline=True
    )
    
    player_embed.add_field(
        name="⏰ Time Remaining",
        value=f"```{round(api.map_data['ranked']['current']['remainingMins']/60, 1)}h```",
        inline=True
    )
    
    player_embed.add_field(
        name="Next Map",
        value=f"```{api.map_data['ranked']['next']['map']}```",
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
    
    # Set footer
    player_embed.set_footer(text=f"last updated {formatted_time} ET")
    
    # Set thumbnail and author
    rank_img_url = ranked_data.get('rankImg', None)
    if rank_img_url:
        player_embed.set_thumbnail(url=rank_img_url)
        player_embed.set_author(
            name=f"{global_data['name']}'s Profile",
            icon_url=rank_img_url
        )
    else:
        player_embed.set_author(name=f"{global_data['name']}'s Profile")
    
    return player_embed


def create_server_status_embed(formatted_time, api):
    """
    Create a Discord embed with server status information.
    
    Args:
        formatted_time (str): Formatted timestamp string
        api (API): API instance with cached data
        
    Returns:
        discord.Embed: Server status embed
    """
    # Define status emojis
    status_emojis = {
        "UP": "🟢",
        "DOWN": "🔴",
        "SLOW": "🟡",
        "UNKNOWN": "⚪"
    }
    
    # Define region flags
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
    
    for region, data in api.matchmaking_server_data.items():
        status = data['Status'].upper()
        emoji = status_emojis.get(status, "⚪")
        flag = region_flags.get(region.upper(), "❓")
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
    
    for region, data in api.crossplay_server_data.items():
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
    
    for platform, data in api.console_server_data.items():
        status = data['Status'].upper()
        emoji = status_emojis.get(status, "⚪")
        server_embed.add_field(
            name=f"{platform}",
            value=f"```{emoji} {status}```",
            inline=True
        )
    
    server_embed.set_footer(text=f"last updated {formatted_time} ET")
    
    # Set thumbnail
    rank_img_url = "https://upload.wikimedia.org/wikipedia/commons/b/b1/Apex_legends_simple_logo.jpg"
    server_embed.set_thumbnail(url=rank_img_url)
    
    return server_embed
