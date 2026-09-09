from __future__ import annotations

import unittest
from datetime import datetime, timezone

from mta_board.config import AppConfig
from mta_board.models import BoardState
from mta_board.service import BoardService
from mta_board.web import _status_payload


class WebTests(unittest.TestCase):
    def test_demo_status_is_live(self) -> None:
        service = BoardService(AppConfig(), demo=True)
        service.update()
        status = _status_payload(service)
        self.assertEqual(status["station_id"], "R05")
        self.assertEqual(status["station_name"], "Broadway")
        self.assertEqual(status["direction_label"], "Manhattan")
        self.assertEqual(status["arrival_count"], 2)
        self.assertFalse(status["stale"])
        self.assertTrue(status["live"])

    def test_api_error_is_not_reported_as_live(self) -> None:
        service = BoardService(AppConfig())
        service._state = BoardState(
            "R05",
            "Broadway",
            "S",
            ("N", "W"),
            updated_at=datetime.now(timezone.utc),
            error="HTTP 503",
        )

        status = _status_payload(service)
        self.assertFalse(status["stale"])
        self.assertFalse(status["live"])
        self.assertEqual(status["error"], "HTTP 503")


if __name__ == "__main__":
    unittest.main()
