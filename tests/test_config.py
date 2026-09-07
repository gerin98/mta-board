from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mta_board.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_broadway_defaults(self) -> None:
        config = load_config(Path(__file__).parents[1] / "config.toml")
        self.assertEqual(config.board.station_id, "R05")
        self.assertEqual(config.board.routes, ("N", "W"))
        self.assertEqual(config.board.direction, "S")
        self.assertEqual(config.board.max_arrivals, 2)

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


if __name__ == "__main__":
    unittest.main()
