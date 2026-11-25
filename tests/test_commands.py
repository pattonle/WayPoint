import unittest
import discord
from discord.ext import commands

from api import API
from commands import setup_all_commands
from database import Database


class TestCommands(unittest.IsolatedAsyncioTestCase):
    async def test_all_commands_registered_with_expected_choices(self):
        intents = discord.Intents.default()
        bot = commands.Bot(command_prefix="!", intents=intents)
        db = Database(db_path=":memory:")
        api = API()

        try:
            await setup_all_commands(bot, db, api)
            cmds = {cmd.name: cmd for cmd in bot.tree.get_commands()}

            expected = {
                "register",
                "unregister",
                "profile",
                "stats",
                "lookup",
                "maps",
                "leaderboard",
                "history",
                "track",
                "setsteam",
                "getsteam",
                "apex_status",
                "sessions_channel",
            }
            self.assertEqual(set(cmds.keys()), expected)

            for cmd_name in ("register", "lookup"):
                platform_param = next(p for p in cmds[cmd_name].parameters if p.name == "platform")
                choice_values = [c.value for c in platform_param.choices]
                self.assertEqual(choice_values, ["PC", "X1", "PS4"])
        finally:
            await api.close()


if __name__ == "__main__":
    unittest.main()
