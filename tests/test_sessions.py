import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from api import API
from commands import user_commands
from database import Database
import tasks


class TestSessionTracking(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "sessions_test.db")
        self.db = Database(db_path=self.db_path)
        await self.db.init()
        self.api = API()
        await self.db.save_server_config(111, sessions_channel_id=333)
        await self.db.save_user(1001, 111, "uid_1", "PC", 9000)
        await self.db.update_user_steam_id(1001, "76561198000000000")

    async def asyncTearDown(self):
        await self.api.close()
        self._tmpdir.cleanup()

    async def test_steam_session_end_does_not_set_manual_time_registered(self):
        feed_channel = MagicMock()
        feed_channel.send = AsyncMock()
        user_obj = MagicMock()
        user_obj.display_name = "Alice"
        user_obj.send = AsyncMock()

        mock_bot = MagicMock()
        mock_bot.get_channel.return_value = feed_channel
        mock_bot.fetch_user = AsyncMock(return_value=user_obj)

        tasks.bot = mock_bot
        tasks.db = self.db
        tasks.api = self.api

        with patch.object(self.api, "get_player_game", AsyncMock(return_value="1172470")), \
             patch.object(self.api, "fetch_player_stats", AsyncMock(return_value={
                 "global": {"name": "Alice", "rank": {"rankName": "Platinum", "rankDiv": 2, "rankScore": 9000}}
             })):
            await tasks.apex_play_monitor.coro()

        user_row = await self.db.get_user(1001)
        self.assertEqual(user_row[11], 1)
        self.assertIsNone(user_row[5])

        with patch.object(self.api, "get_player_game", AsyncMock(return_value=None)), \
             patch.object(self.api, "fetch_player_stats", AsyncMock(return_value={
                 "global": {"name": "Alice", "rank": {"rankName": "Platinum", "rankDiv": 1, "rankScore": 9180}}
             })):
            await tasks.apex_play_monitor.coro()

        user_row = await self.db.get_user(1001)
        self.assertEqual(user_row[4], 9180)
        self.assertEqual(user_row[11], 0)
        # Critical regression check: Steam session end must NOT populate manual /track timestamp
        self.assertIsNone(user_row[5])

        sessions = await self.db.get_user_sessions(1001)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0][2], 180)
        self.assertEqual(sessions[0][5], "steam")
        feed_channel.send.assert_awaited_once()
        user_obj.send.assert_awaited_once()

    async def test_manual_track_start_and_stop_records_session(self):
        feed_channel = MagicMock()
        feed_channel.send = AsyncMock()
        mock_bot = MagicMock()
        mock_bot.get_channel.return_value = feed_channel

        user_commands.bot = mock_bot
        user_commands.db = self.db
        user_commands.api = self.api

        def _make_interaction():
            interaction = MagicMock()
            interaction.user = SimpleNamespace(id=1001, display_name="Alice")
            interaction.guild = SimpleNamespace(id=111)
            interaction.response = MagicMock()
            interaction.response.defer = AsyncMock()
            interaction.followup = MagicMock()
            interaction.followup.send = AsyncMock()
            return interaction

        # Start manual tracking
        with patch.object(self.api, "fetch_player_stats", AsyncMock(return_value={
            "global": {"rank": {"rankName": "Platinum", "rankDiv": 2, "rankScore": 9000}}
        })):
            await user_commands.track.callback(_make_interaction())

        started_row = await self.db.get_user(1001)
        self.assertIsNotNone(started_row[5])

        # Stop manual tracking
        with patch.object(self.api, "fetch_player_stats", AsyncMock(return_value={
            "global": {"rank": {"rankName": "Platinum", "rankDiv": 1, "rankScore": 9120}}
        })):
            await user_commands.track.callback(_make_interaction())

        stopped_row = await self.db.get_user(1001)
        self.assertIsNone(stopped_row[5])
        self.assertEqual(stopped_row[4], 9120)

        sessions = await self.db.get_user_sessions(1001)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0][2], 120)
        self.assertEqual(sessions[0][5], "manual")
        feed_channel.send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
