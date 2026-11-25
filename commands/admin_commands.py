"""
Admin commands for the WayPoint Discord bot.
"""
import discord
from discord import app_commands
from datetime import datetime
from config import ADMIN_ROLE, TIMEZONE_ET
from embeds import create_server_status_embed


# Module-level variables (will be set by setup)
bot = None
db = None
api = None


async def setup(bot_instance, db_instance, api_instance):
    """Register all admin commands with the bot."""
    global bot, db, api
    bot = bot_instance
    db = db_instance
    api = api_instance

    bot.tree.add_command(apex_status)
    bot.tree.add_command(sessions_channel)

    print("✅ Admin commands registered")


@app_commands.command(name="apex_status", description="Registers server status channel and updates the status message")
@app_commands.checks.has_role(ADMIN_ROLE)
async def apex_status(interaction: discord.Interaction):
    """Register a channel for server status updates and post the initial status message."""
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.HTTPException):
        return

    apex_server_status_channel = interaction.channel.id
    server = await db.get_server(interaction.guild.id)
    apex_server_message_id = server[2] if server and len(server) > 2 else None

    await db.save_server_config(
        discord_server_id=interaction.guild.id,
        apex_server_channel_id=apex_server_status_channel
    )

    channel = bot.get_channel(apex_server_status_channel)
    if not channel:
        await interaction.followup.send("❌ Could not find the specified channel.", ephemeral=True)
        return

    await api.fetch_all_data()
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    server_embed = create_server_status_embed(formatted_time, api)

    if apex_server_message_id:
        try:
            message = await channel.fetch_message(apex_server_message_id)
            await message.edit(embed=server_embed)
        except discord.NotFound:
            message = await channel.send(embed=server_embed)
    else:
        message = await channel.send(embed=server_embed)

    await db.save_server_config(
        discord_server_id=interaction.guild.id,
        apex_server_message_id=message.id
    )

    try:
        await interaction.followup.send(
            f"✅ Server status channel ID {apex_server_status_channel} saved and message updated!",
            ephemeral=True
        )
    except discord.errors.NotFound:
        pass


@app_commands.command(name="sessions_channel", description="Set the current channel to receive completed RP session summaries")
@app_commands.checks.has_role(ADMIN_ROLE)
async def sessions_channel(interaction: discord.Interaction):
    """Set the current channel as the server's RP session summary feed."""
    await interaction.response.defer(ephemeral=True)
    await db.save_server_config(
        discord_server_id=interaction.guild.id,
        sessions_channel_id=interaction.channel.id
    )
    await interaction.followup.send(
        f"✅ Session summaries will now be posted in {interaction.channel.mention}!",
        ephemeral=True
    )
