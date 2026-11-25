import unittest
from unittest.mock import AsyncMock, MagicMock

from api import API
import embeds


class TestApiAndEmbeds(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = API()

    async def asyncTearDown(self):
        await self.api.close()

    def test_get_predcap_value(self):
        self.api.predcap_data = {"PC": {"val": 25000}, "X1": {"val": 18000}}
        self.assertEqual(self.api.get_predcap_value("PC"), 25000)
        self.assertEqual(self.api.get_predcap_value("X1"), 18000)
        self.assertEqual(self.api.get_predcap_value("PS4"), 0)

    async def test_fetch_bridge_raises_on_api_error_payload(self):
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value={"Error": "Player not found"})

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_resp

        mock_session = MagicMock()
        mock_session.get.return_value = mock_cm
        mock_session.closed = False
        mock_session.close = AsyncMock()
        self.api._session = mock_session

        with self.assertRaises(ValueError):
            await self.api.fetch_player_stats_by_name("Nobody", "PC")

    async def test_embeds_handle_empty_global_cache_safely(self):
        player_payload = {
            "global": {
                "name": "TestPlayer",
                "uid": "uid_1",
                "rank": {"rankName": "Diamond", "rankDiv": 3, "rankScore": 12500},
            }
        }
        stats_embed = await embeds.create_player_stats_embed(
            "PC", "uid_1", "11/25/2026 9:55 AM", self.api, player_data=player_payload
        )
        self.assertIn("APEX LEGENDS STATS", stats_embed.title)

        server_embed = embeds.create_server_status_embed("11/25/2026 9:55 AM", self.api)
        self.assertIn("SERVER STATUS", server_embed.title)

        maps_embed = embeds.create_maps_embed(self.api, "11/25/2026 9:55 AM")
        self.assertIn("MAP ROTATION", maps_embed.title)

        lb_embed = embeds.create_leaderboard_embed("Test Guild", [], "11/25/2026 9:55 AM")
        self.assertIn("Leaderboard", lb_embed.title)

        summary_embed = embeds.create_session_summary_embed(
            "TestPlayer", 9000, 9240, "1h 30m", "+160.0 RP/hr", "Diamond 3", source="steam"
        )
        self.assertIn("TestPlayer", summary_embed.title)

        history_embed = embeds.create_history_embed(
            "TestPlayer", [], (0, 0, 0, 0), "11/25/2026 9:55 AM"
        )
        self.assertIn("TestPlayer", history_embed.title)


if __name__ == "__main__":
    unittest.main()
