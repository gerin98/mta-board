from __future__ import annotations

import errno
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from mta_board.config import AppConfig
from mta_board.models import BoardState
from mta_board.service import BoardService
from mta_board.web import _status_payload, serve_preview


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

    @patch("mta_board.web.webbrowser.open")
    @patch("mta_board.web._is_mta_board_preview", return_value=True)
    @patch(
        "mta_board.web.ThreadingHTTPServer",
        side_effect=OSError(errno.EADDRINUSE, "Address already in use"),
    )
    def test_existing_preview_is_opened_instead_of_failing(
        self,
        _server: MagicMock,
        _is_preview: MagicMock,
        open_browser: MagicMock,
    ) -> None:
        service = MagicMock(spec=BoardService)

        serve_preview(service, "127.0.0.1", 8000)

        service.start.assert_not_called()
        open_browser.assert_called_once_with("http://127.0.0.1:8000")

    @patch("mta_board.web._is_mta_board_preview", return_value=False)
    @patch(
        "mta_board.web.ThreadingHTTPServer",
        side_effect=OSError(errno.EADDRINUSE, "Address already in use"),
    )
    def test_unrelated_port_conflict_still_fails(
        self,
        _server: MagicMock,
        _is_preview: MagicMock,
    ) -> None:
        service = MagicMock(spec=BoardService)

        with self.assertRaises(OSError) as raised:
            serve_preview(service, "127.0.0.1", 8000)

        self.assertEqual(raised.exception.errno, errno.EADDRINUSE)
        service.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
