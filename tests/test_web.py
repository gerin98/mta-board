from __future__ import annotations

import unittest

from mta_board.config import AppConfig
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


if __name__ == "__main__":
    unittest.main()
