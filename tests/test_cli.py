from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone

from mta_board.__main__ import check_feed
from mta_board.models import Arrival, BoardState


class FakeService:
    def __init__(self, state: BoardState) -> None:
        self._state = state
        self.updated = False

    def update(self) -> None:
        self.updated = True

    def state(self) -> BoardState:
        return self._state


class CheckFeedTests(unittest.TestCase):
    def test_reports_a_successful_live_check(self) -> None:
        now = datetime(2026, 9, 12, 20, 0, tzinfo=timezone.utc)
        service = FakeService(
            BoardState(
                "127",
                "Times Sq-42 St",
                "N",
                ("1", "2", "3"),
                (Arrival("1", "Van Cortlandt Park-242 St", now),),
                now,
            )
        )

        output = io.StringIO()
        with redirect_stdout(output):
            check_feed(service, require_arrivals=True)  # type: ignore[arg-type]

        self.assertTrue(service.updated)
        self.assertIn("MTA feed OK", output.getvalue())
        self.assertIn("1 arrivals", output.getvalue())

    def test_fails_when_the_service_reports_an_error(self) -> None:
        service = FakeService(BoardState("127", "Times Sq-42 St", "N", ("1",), error="HTTP 503"))

        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            check_feed(service)  # type: ignore[arg-type]

    def test_can_require_at_least_one_arrival(self) -> None:
        now = datetime(2026, 9, 12, 20, 0, tzinfo=timezone.utc)
        service = FakeService(BoardState("127", "Times Sq-42 St", "N", ("1",), updated_at=now))

        with self.assertRaisesRegex(RuntimeError, "no matching upcoming trains"):
            check_feed(service, require_arrivals=True)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
