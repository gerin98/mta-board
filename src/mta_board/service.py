from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from PIL import Image

from .config import AppConfig
from .models import Arrival, BoardState
from .mta import StopCatalog, fetch_arrivals
from .render import render_board


class BoardService:
    def __init__(self, config: AppConfig, demo: bool = False) -> None:
        self.config = config
        self.demo = demo
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stops: dict[str, str] = {}
        self._state = BoardState(
            station_id=config.board.station_id,
            station_name=config.board.station_id,
            direction=config.board.direction,
            routes=config.board.routes,
            error="Waiting for MTA data",
        )

    def _demo_arrivals(self, now: datetime) -> tuple[Arrival, ...]:
        routes = self.config.board.routes or ("N", "W")
        destinations = ("Coney Island-Stillwell Av", "Whitehall St-South Ferry", "Coney Island-Stillwell Av")
        minutes = (2, 7, 12)
        return tuple(
            Arrival(
                route=routes[index % len(routes)],
                destination=destinations[index],
                arrival_time=now + timedelta(minutes=minute),
                trip_id=f"demo-{index}",
            )
            for index, minute in enumerate(minutes[: self.config.board.max_arrivals])
        )

    def update(self) -> None:
        now = datetime.now(timezone.utc)
        try:
            if self.demo:
                stops = {self.config.board.station_id: "Broadway"}
                arrivals = self._demo_arrivals(now)
            else:
                if not self._stops:
                    self._stops = StopCatalog().load(self.config.network.request_timeout_seconds)
                stops = self._stops
                station_name = stops.get(self.config.board.station_id)
                if not station_name:
                    raise ValueError(f"station ID {self.config.board.station_id} was not found in MTA static GTFS")
                arrivals = fetch_arrivals(self.config, stops, now=now)
            station_name = stops.get(self.config.board.station_id, self.config.board.station_id)
            new_state = BoardState(
                station_id=self.config.board.station_id,
                station_name=station_name,
                direction=self.config.board.direction,
                routes=self.config.board.routes,
                arrivals=arrivals,
                updated_at=now,
            )
        except Exception as exc:
            with self._lock:
                previous = self._state
            new_state = BoardState(
                station_id=previous.station_id,
                station_name=previous.station_name,
                direction=previous.direction,
                routes=previous.routes,
                arrivals=previous.arrivals,
                updated_at=previous.updated_at,
                error=str(exc),
            )
        with self._lock:
            self._state = new_state

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.update()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll, name="mta-feed", daemon=True)
        self._thread.start()

    def _poll(self) -> None:
        while not self._stop_event.wait(self.config.network.feed_refresh_seconds):
            self.update()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def state(self) -> BoardState:
        with self._lock:
            return self._state

    def frame(self, now: datetime | None = None) -> Image.Image:
        return render_board(self.state(), self.config, now=now)

