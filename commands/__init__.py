"""
Command setup orchestration for the WayPoint Discord bot.
"""
from commands import user_commands, admin_commands


async def setup_all_commands(bot, db, api):
    """
    Set up all bot commands (user and admin).
    
    Args:
        bot: Discord bot instance
        db: Database instance
        api: API instance
    """
    await user_commands.setup(bot, db, api)
    await admin_commands.setup(bot, db, api)
    print("✅ All commands registered")
