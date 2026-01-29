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
    """
    Register all admin commands with the bot.
    
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
    bot.tree.add_command(register_server_id)
    bot.tree.add_command(register_server_status)
    
    print("✅ Admin commands registered")


@app_commands.command(name="register_server_id", description="Saves server ID and configuration to the database")
@app_commands.checks.has_role(ADMIN_ROLE)
async def register_server_id(interaction: discord.Interaction):
    """
    Register the current Discord server in the database.
    
    Args:
        interaction: Discord interaction
    """
    discord_server_id = interaction.guild.id
    
    await db.save_server_config(discord_server_id=discord_server_id)
    
    await interaction.response.send_message(
        f"✅ Server ID {discord_server_id} and configuration saved to the database!",
        ephemeral=True
    )


@app_commands.command(name="register_server_status", description="Registers server status channel and updates the status message")
@app_commands.checks.has_role(ADMIN_ROLE)
async def register_server_status(interaction: discord.Interaction):
    """
    Register a channel for server status updates and post the initial status message.
    
    Args:
        interaction: Discord interaction
    """
    # Try to defer, if it fails the interaction has expired
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.errors.NotFound, discord.errors.HTTPException):
        # Interaction already expired, we can't respond
        return
    
    apex_server_status_channel = interaction.channel.id
    
    # Get existing server config
    server = await db.get_server(interaction.guild.id)
    apex_server_message_id = server[2] if server else None
    
    # Save channel configuration
    await db.save_server_config(
        discord_server_id=interaction.guild.id,
        apex_server_channel_id=apex_server_status_channel
    )
    
    channel = bot.get_channel(apex_server_status_channel)
    if not channel:
        await interaction.followup.send("❌ Could not find the specified channel.", ephemeral=True)
        return
    
    # Fetch API data before creating the embed
    await api.fetch_all_data()
    
    # Create timestamp
    now_et = datetime.now(TIMEZONE_ET)
    formatted_time = now_et.strftime("%m/%d/%Y %I:%M %p").lstrip("0")
    
    # Create the server embed
    server_embed = create_server_status_embed(formatted_time, api)
    
    # Check if a message already exists and edit it, otherwise send a new one
    if apex_server_message_id:
        try:
            message = await channel.fetch_message(apex_server_message_id)
            await message.edit(embed=server_embed)
        except discord.NotFound:
            message = await channel.send(embed=server_embed)
    else:
        message = await channel.send(embed=server_embed)
    
    # Update the database with the new message ID
    await db.save_server_config(
        discord_server_id=interaction.guild.id,
        apex_server_message_id=message.id
    )
    
    # Send success message at the end
    try:
        await interaction.followup.send(
            f"✅ Server status channel ID {apex_server_status_channel} saved and message updated!",
            ephemeral=True
        )
    except discord.errors.NotFound:
        # Interaction expired, but the operation still completed successfully
        pass
