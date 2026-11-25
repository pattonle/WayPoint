import os
import tempfile
import unittest
from datetime import datetime, timedelta

import config
from database import Database


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self.db = Database(db_path=self.db_path)
        await self.db.init()

    async def asyncTearDown(self):
        self._tmpdir.cleanup()

    async def test_server_config_crud(self):
        await self.db.save_server_config(111, apex_server_channel_id=222, sessions_channel_id=333)
        row = await self.db.get_server(111)
        self.assertEqual(row, (111, 222, None, 333))

        await self.db.save_server_config(111, apex_server_message_id=444)
        row = await self.db.get_server(111)
        self.assertEqual(row, (111, 222, 444, 333))

    async def test_user_and_steam_crud(self):
        await self.db.save_user(1001, 111, "uid_1", "PC", 9000)
        self.assertTrue(await self.db.update_user_steam_id(1001, "76561198000000000"))
        self.assertFalse(await self.db.update_user_steam_id(9999, "76561198000000000"))

        server_users = await self.db.get_server_users(111)
        self.assertEqual(len(server_users), 1)
        self.assertEqual(server_users[0][8], "76561198000000000")

        self.assertTrue(await self.db.delete_user(1001))
        self.assertIsNone(await self.db.get_user(1001))

    async def test_session_history_and_totals(self):
        await self.db.save_user(1001, 111, "uid_1", "PC", 9000)
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        await self.db.record_session(1001, 111, 9000, 9240, t0, t0 + timedelta(hours=1), source="steam")
        await self.db.record_session(1001, 111, 9240, 9190, t0 + timedelta(hours=2), t0 + timedelta(hours=3), source="manual")

        sessions = await self.db.get_user_sessions(1001, limit=5)
        totals = await self.db.get_user_session_totals(1001)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0][5], "manual")
        self.assertEqual(totals, (2, 190, 240, -50))


if __name__ == "__main__":
    unittest.main()
