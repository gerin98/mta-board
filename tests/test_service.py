from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from mta_board.config import AppConfig
from mta_board.models import Arrival
from mta_board.service import BoardService


class ServiceTests(unittest.TestCase):
    def test_api_failure_keeps_last_successful_arrivals(self) -> None:
        service = BoardService(AppConfig())
        service._stops = {"R05": "Broadway"}
        arrival = Arrival(
            "N",
            "Coney Island-Stillwell Av",
            datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        with patch("mta_board.service.fetch_arrivals", return_value=(arrival,)):
            service.update()
        successful = service.state()

        with patch("mta_board.service.fetch_arrivals", side_effect=RuntimeError("HTTP 503")):
            service.update()
        failed = service.state()

        self.assertEqual(failed.arrivals, successful.arrivals)
        self.assertEqual(failed.updated_at, successful.updated_at)
        self.assertEqual(failed.error, "HTTP 503")


if __name__ == "__main__":
    unittest.main()
