from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from mta_board.config import AppConfig
from mta_board.models import Arrival, BoardState
from mta_board.render import ROUTE_COLORS, render_board


class RenderTests(unittest.TestCase):
    def test_frame_is_128_by_32_and_contains_nw_yellow(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            station_id="R05",
            station_name="Broadway",
            direction="S",
            routes=("N", "W"),
            arrivals=(
                Arrival("N", "Coney Island-Stillwell Av", now + timedelta(minutes=3)),
                Arrival("W", "Whitehall St-South Ferry", now + timedelta(minutes=8)),
            ),
            updated_at=now,
        )
        frame = render_board(state, AppConfig(), now=now)
        self.assertEqual(frame.size, (128, 32))
        for x in range(128):
            self.assertEqual(frame.getpixel((x, 0)), (0, 0, 0))
            self.assertEqual(frame.getpixel((x, 31)), (0, 0, 0))
        for y in range(32):
            self.assertEqual(frame.getpixel((0, y)), (0, 0, 0))
            self.assertEqual(frame.getpixel((127, y)), (0, 0, 0))
        colors = {color for _, color in frame.getcolors(maxcolors=128 * 32) or []}
        self.assertIn(ROUTE_COLORS["N"], colors)

    def test_stale_frame_contains_red_status_area(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState("R05", "Broadway", "S", ("N", "W"))
        frame = render_board(state, AppConfig(), now=now)
        self.assertEqual(frame.getpixel((1, 30)), (70, 0, 0))
        self.assertEqual(frame.getpixel((0, 31)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
