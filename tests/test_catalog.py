from __future__ import annotations

import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO

from mta_board.catalog import load_catalog, resolve_station, search_stations
from mta_board.__main__ import list_stations


class CatalogTests(unittest.TestCase):
    def test_catalog_contains_all_current_station_records(self) -> None:
        stations = load_catalog()
        self.assertEqual(len(stations), 496)
        broadway = next(station for station in stations if station.id == "R05")
        self.assertEqual(broadway.name, "Broadway")
        self.assertEqual(broadway.routes, ("N", "W"))
        self.assertEqual(broadway.south_label, "Manhattan")

    def test_search_disambiguates_broadway_with_line(self) -> None:
        matches = search_stations("Broadway Astoria")
        self.assertEqual([station.id for station in matches], ["R05"])

    def test_exact_id_resolves_station(self) -> None:
        self.assertEqual(resolve_station("r05").id, "R05")

    def test_route_name_disambiguates_times_square(self) -> None:
        self.assertEqual(resolve_station("Times Sq 7").id, "725")

    def test_street_number_is_not_forced_to_route(self) -> None:
        self.assertEqual(resolve_station("1 Av").id, "L06")

    def test_ambiguous_name_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve_station("Broadway")

    def test_cli_formats_station_as_readable_card(self) -> None:
        output = StringIO()
        args = Namespace(query=["Times Sq", "2", "3"], limit=5, json=False)
        with redirect_stdout(output):
            list_stations(args)
        self.assertEqual(
            output.getvalue(),
            "127 — Times Sq-42 St\n"
            "  Location:   Manhattan · Broadway - 7Av\n"
            "  Trains:     1, 2, 3\n"
            "  Direction N: Uptown\n"
            "  Direction S: Downtown\n",
        )


if __name__ == "__main__":
    unittest.main()
