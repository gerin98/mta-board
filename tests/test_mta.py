from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from google.transit import gtfs_realtime_pb2

from mta_board.config import AppConfig, BoardConfig
from mta_board.mta import feeds_for_routes, parse_arrivals


NOW = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)


def make_feed(trips: list[dict]) -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    for index, trip in enumerate(trips):
        entity = feed.entity.add()
        entity.id = str(index)
        update = entity.trip_update
        update.trip.trip_id = trip.get("trip_id", f"trip-{index}")
        update.trip.route_id = trip["route"]
        for stop_id, minute in trip["stops"]:
            stop = update.stop_time_update.add()
            stop.stop_id = stop_id
            stop.arrival.time = int((NOW + timedelta(minutes=minute)).timestamp())
    return feed.SerializeToString()


class MtaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig(board=BoardConfig())
        self.stops = {
            "R05": "Broadway",
            "R05N": "Broadway",
            "R05S": "Broadway",
            "R27": "Whitehall St-South Ferry",
            "R46": "Coney Island-Stillwell Av",
        }

    def test_routes_choose_one_nqrw_feed(self) -> None:
        self.assertEqual(feeds_for_routes(("N", "W")), ("gtfs-nqrw",))

    def test_filters_direction_route_and_expired_trains(self) -> None:
        payload = make_feed([
            {"route": "N", "trip_id": "n-good", "stops": [("R05S", 3), ("R46S", 35)]},
            {"route": "W", "trip_id": "w-good", "stops": [("R05S", 8), ("R27S", 30)]},
            {"route": "Q", "stops": [("R05S", 4), ("R46S", 40)]},
            {"route": "N", "stops": [("R05N", 2), ("R01N", 10)]},
            {"route": "N", "stops": [("R05S", -1), ("R46S", 30)]},
        ])
        arrivals = parse_arrivals([payload], self.config, self.stops, now=NOW)
        self.assertEqual([arrival.route for arrival in arrivals], ["N", "W"])
        self.assertEqual(arrivals[0].destination, "Coney Island-Stillwell Av")
        self.assertEqual(arrivals[1].destination, "Whitehall St-South Ferry")

    def test_applies_lead_time_and_max_arrivals(self) -> None:
        board = replace(self.config.board, minimum_lead_minutes=5, max_arrivals=1)
        config = replace(self.config, board=board)
        payload = make_feed([
            {"route": "N", "stops": [("R05S", 3), ("R46S", 30)]},
            {"route": "W", "stops": [("R05S", 7), ("R27S", 25)]},
            {"route": "N", "stops": [("R05S", 10), ("R46S", 35)]},
        ])
        arrivals = parse_arrivals([payload], config, self.stops, now=NOW)
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(arrivals[0].route, "W")

    def test_rejects_unknown_route(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported route"):
            feeds_for_routes(("NOPE",))


if __name__ == "__main__":
    unittest.main()

