import unittest
from datetime import datetime, timedelta

import config
import utils


class TestUtils(unittest.TestCase):
    def test_format_time_difference_under_one_day(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        t1 = t0 + timedelta(hours=3, minutes=4, seconds=5)
        self.assertEqual(
            utils.format_time_difference(t0, t1),
            "3 hours, 4 minutes, 5 seconds",
        )

    def test_format_time_difference_multi_day_does_not_overflow_hours(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        t1 = t0 + timedelta(days=1, hours=2, minutes=15, seconds=30)
        self.assertEqual(
            utils.format_time_difference(t0, t1),
            "1 days, 2 hours, 15 minutes, 30 seconds",
        )

    def test_format_time_difference_negative_clamps_to_zero(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        self.assertEqual(
            utils.format_time_difference(t0, t0 - timedelta(minutes=5)),
            "0 hours, 0 minutes, 0 seconds",
        )

    def test_format_duration_short(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        self.assertEqual(utils.format_duration_short(t0, t0 + timedelta(minutes=1)), "1 minute")
        self.assertEqual(utils.format_duration_short(t0, t0 + timedelta(minutes=45)), "45 minutes")
        self.assertEqual(utils.format_duration_short(t0, t0 + timedelta(hours=2)), "2h")
        self.assertEqual(utils.format_duration_short(t0, t0 + timedelta(hours=2, minutes=15)), "2h 15m")

    def test_format_rp_per_hour(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=config.TIMEZONE_ET)
        self.assertEqual(utils.format_rp_per_hour(200, t0, t0 + timedelta(hours=2)), "+100.0 RP/hr")
        self.assertEqual(utils.format_rp_per_hour(-50, t0, t0 + timedelta(hours=2)), "-25.0 RP/hr")
        self.assertEqual(utils.format_rp_per_hour(0, t0, t0 + timedelta(hours=2)), "0.0 RP/hr")
        self.assertEqual(utils.format_rp_per_hour(100, t0, t0), "0.0 RP/hr")

    def test_parse_timestamp_applies_timezone_to_naive(self):
        parsed = utils.parse_timestamp("2026-01-01T10:00:00", config.TIMEZONE_ET)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, config.TIMEZONE_ET)
        self.assertIsNone(utils.parse_timestamp(None, config.TIMEZONE_ET))


if __name__ == "__main__":
    unittest.main()
