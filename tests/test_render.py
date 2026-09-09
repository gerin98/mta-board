from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from mta_board.config import AppConfig
from mta_board.catalog import resolve_station
from mta_board.models import Arrival, BoardState
from mta_board.render import (
    LINE_COLOR,
    ROUTE_COLORS,
    STATION_COLOR,
    _header_parts,
    _scroll_offset,
    _text_width,
    render_board,
)


class RenderTests(unittest.TestCase):
    def test_scroll_waits_travels_holds_and_repeats(self) -> None:
        started = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=4), started, 20), 0)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=5.5), started, 20), 6)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=8), started, 20), 20)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=9), started, 20), 0)

    def test_shorter_rows_reset_on_longest_row_cycle(self) -> None:
        started = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=6), started, 10, 20), 10)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=8), started, 10, 20), 10)
        self.assertEqual(_scroll_offset(started + timedelta(seconds=9), started, 10, 20), 0)

    def test_header_combines_station_name_and_direction(self) -> None:
        self.assertEqual(
            _header_parts(resolve_station("R09"), "S", 126),
            ("QNSBORO PLZ", "MANHATTAN"),
        )
        self.assertEqual(
            _header_parts(resolve_station("629"), "S", 126),
            ("59 ST", "DOWNTOWN"),
        )
        self.assertEqual(
            _header_parts(resolve_station("R05"), "S", 126),
            ("BROADWAY", "MANHATTAN"),
        )

    def test_ellipsis_dots_are_tightly_spaced(self) -> None:
        self.assertEqual(_text_width("..."), 9)

    def test_long_text_scrolls_and_toggle_can_freeze_it(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            station_id="629",
            station_name="59 St",
            direction="S",
            routes=("6",),
            arrivals=(
                Arrival("6", "Brooklyn Bridge-City Hall", now + timedelta(minutes=3, seconds=30)),
            ),
            updated_at=now,
        )
        scrolling = AppConfig()
        frozen = replace(scrolling, display=replace(scrolling.display, scrolling=False))

        self.assertNotEqual(
            render_board(state, scrolling, now=now).tobytes(),
            render_board(state, scrolling, now=now + timedelta(seconds=6)).tobytes(),
        )
        self.assertEqual(
            render_board(state, frozen, now=now).tobytes(),
            render_board(state, frozen, now=now + timedelta(seconds=6)).tobytes(),
        )

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

    def test_fresh_api_error_is_shown_instead_of_no_trains(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            "R05",
            "Broadway",
            "S",
            ("N", "W"),
            updated_at=now,
            error="HTTP 503",
        )

        frame = render_board(state, AppConfig(), now=now)
        self.assertEqual(frame.getpixel((1, 21)), (70, 0, 0))

    def test_successful_empty_feed_shows_no_upcoming_trains(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState("R05", "Broadway", "S", ("N", "W"), updated_at=now)

        frame = render_board(state, AppConfig(), now=now)
        self.assertNotEqual(frame.getpixel((1, 21)), (70, 0, 0))
        self.assertIn((252, 204, 10), {color for _, color in frame.getcolors() or []})

    def test_single_character_route_is_centered_in_bullet(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            station_id="629",
            station_name="59 St",
            direction="S",
            routes=("A",),
            arrivals=(Arrival("A", "Far Rockaway", now + timedelta(minutes=3)),),
            updated_at=now,
        )

        frame = render_board(state, AppConfig(), now=now)
        white_pixels = [
            (x, y)
            for y in range(10, 20)
            for x in range(1, 11)
            if frame.getpixel((x, y)) == (255, 255, 255)
        ]

        self.assertEqual(min(x for x, _ in white_pixels), 3)
        self.assertEqual(max(x for x, _ in white_pixels), 7)
        self.assertEqual(min(y for _, y in white_pixels), 12)
        self.assertEqual(max(y for _, y in white_pixels), 16)

    def test_route_bullet_has_a_round_pixel_silhouette(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            "R05",
            "Broadway",
            "S",
            ("W",),
            (Arrival("W", "Whitehall St", now + timedelta(minutes=3)),),
            now,
        )

        frame = render_board(state, AppConfig(), now=now)
        yellow = ROUTE_COLORS["W"]
        self.assertEqual([frame.getpixel((x, 10)) for x in range(1, 10)].count(yellow), 5)
        self.assertEqual(frame.getpixel((1, 14)), yellow)
        self.assertEqual(frame.getpixel((9, 14)), yellow)
        self.assertEqual(frame.getpixel((1, 10)), (0, 0, 0))
        self.assertEqual(frame.getpixel((9, 10)), (0, 0, 0))

    def test_countdown_has_four_pixel_left_gap(self) -> None:
        now = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)
        state = BoardState(
            station_id="R05",
            station_name="Broadway",
            direction="S",
            routes=("N",),
            arrivals=(
                Arrival(
                    "N",
                    "Coney Island-Stillwell Avenue",
                    now + timedelta(minutes=3),
                ),
            ),
            updated_at=now,
        )

        frame = render_board(state, AppConfig(), now=now)
        countdown_x = 127 - _text_width("3 min")
        for x in range(countdown_x - 4, countdown_x):
            for y in range(11, 18):
                self.assertEqual(frame.getpixel((x, y)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
