from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from mta_board.config import AppConfig
from mta_board.catalog import resolve_station
from mta_board.models import Arrival, BoardState
from mta_board.render import (
    LINE_COLOR,
    ROUTE_COLORS,
    STATION_COLOR,
    _header_parts,
    _text_width,
    render_board,
)


class RenderTests(unittest.TestCase):
    def test_header_combines_station_identity_and_direction(self) -> None:
        self.assertEqual(
            _header_parts(resolve_station("R09"), "S", 126),
            ("QNSBORO PLZ", "MANHATTAN"),
        )
        self.assertEqual(
            _header_parts(resolve_station("629"), "S", 126),
            ("59 ST LEX AV", "DTWN"),
        )

    def test_ellipsis_dots_are_tightly_spaced(self) -> None:
        self.assertEqual(_text_width("..."), 9)

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
        # The station header occupies the top band; arrivals begin below it.
        self.assertTrue(any(frame.getpixel((x, 2)) == STATION_COLOR for x in range(1, 127)))
        self.assertTrue(any(frame.getpixel((x, 2)) == LINE_COLOR for x in range(1, 127)))
        self.assertTrue(any(frame.getpixel((x, 8)) == LINE_COLOR for x in range(1, 127)))
        self.assertEqual(frame.getpixel((5, 10)), ROUTE_COLORS["N"])

    def test_stale_frame_contains_red_status_area(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState("R05", "Broadway", "S", ("N", "W"))
        frame = render_board(state, AppConfig(), now=now)
        self.assertEqual(frame.getpixel((1, 30)), (70, 0, 0))
        self.assertEqual(frame.getpixel((0, 31)), (0, 0, 0))

    def test_single_character_route_is_centered_in_bullet(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            station_id="629",
            station_name="59 St",
            direction="S",
            routes=("6",),
            arrivals=(Arrival("6", "Brooklyn Bridge-City Hall", now + timedelta(minutes=3)),),
            updated_at=now,
        )

        frame = render_board(state, AppConfig(), now=now)
        white_pixels = [
            (x, y)
            for y in range(10, 20)
            for x in range(1, 11)
            if frame.getpixel((x, y)) == (255, 255, 255)
        ]

        self.assertEqual(min(x for x, _ in white_pixels), 4)
        self.assertEqual(max(x for x, _ in white_pixels), 8)


if __name__ == "__main__":
    unittest.main()
