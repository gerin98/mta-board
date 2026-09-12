from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from mta_board.config import load_config, save_config
from mta_board_cli.main import configure_board


class ConfigTests(unittest.TestCase):
    def test_loads_broadway_defaults(self) -> None:
        config = load_config(Path(__file__).parents[1] / "config.toml")
        self.assertEqual(config.board.station_id, "R05")
        self.assertEqual(config.board.routes, ("N", "W"))
        self.assertEqual(config.board.direction, "S")
        self.assertEqual(config.board.max_arrivals, 2)
        self.assertTrue(config.display.scrolling)

    def test_rejects_direction_suffix_in_base_station_id(self) -> None:
        content = """[board]
station_id = "R05S"
routes = ["N"]
direction = "S"
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "base GTFS ID"):
                load_config(path)

    def test_rejects_unsupported_route(self) -> None:
        content = """[board]
station_id = "R05"
routes = ["NOPE"]
direction = "S"
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported route"):
                load_config(path)

    def test_save_config_round_trips(self) -> None:
        original = load_config(Path(__file__).parents[1] / "config.toml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            save_config(original, path)
            self.assertEqual(load_config(path), original)

    def test_configure_changes_station_routes_and_direction(self) -> None:
        original = load_config(Path(__file__).parents[1] / "config.toml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            save_config(original, path)
            args = Namespace(
                config=str(path),
                station="59 lex 6",
                routes="6",
                direction="S",
                minimum_lead=None,
            )
            with redirect_stdout(StringIO()):
                configure_board(args)

            updated = load_config(path)
            self.assertEqual(updated.board.station_id, "629")
            self.assertEqual(updated.board.routes, ("6",))
            self.assertEqual(updated.board.direction, "S")

    def test_configure_rejects_route_not_served_at_station(self) -> None:
        original = load_config(Path(__file__).parents[1] / "config.toml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            save_config(original, path)
            args = Namespace(
                config=str(path),
                station="59 lex 6",
                routes="N",
                direction="S",
                minimum_lead=None,
            )
            with self.assertRaisesRegex(ValueError, "does not serve"):
                configure_board(args)

    def test_configure_maps_friendly_shuttle_route_to_realtime_route(self) -> None:
        original = load_config(Path(__file__).parents[1] / "config.toml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            save_config(original, path)
            args = Namespace(
                config=str(path),
                station="902",
                routes="S",
                direction="S",
                minimum_lead=None,
            )
            with redirect_stdout(StringIO()):
                configure_board(args)

            self.assertEqual(load_config(path).board.routes, ("GS",))

    def test_configure_can_disable_scrolling(self) -> None:
        original = load_config(Path(__file__).parents[1] / "config.toml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            save_config(original, path)
            args = Namespace(
                config=str(path),
                station=None,
                routes=None,
                direction=None,
                minimum_lead=None,
                scrolling=False,
            )
            with redirect_stdout(StringIO()):
                configure_board(args)

            self.assertFalse(load_config(path).display.scrolling)


if __name__ == "__main__":
    unittest.main()
