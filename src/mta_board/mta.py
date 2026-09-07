from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.transit import gtfs_realtime_pb2

from .config import AppConfig
from .models import Arrival

STATIC_GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
REALTIME_BASE = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F"

FEED_ROUTES: dict[str, frozenset[str]] = {
    "gtfs": frozenset({"1", "2", "3", "4", "5", "6", "6X", "7", "7X", "GS"}),
    "gtfs-ace": frozenset({"A", "C", "E", "H"}),
    "gtfs-bdfm": frozenset({"B", "D", "F", "FX", "M", "FS"}),
    "gtfs-g": frozenset({"G"}),
    "gtfs-jz": frozenset({"J", "Z"}),
    "gtfs-nqrw": frozenset({"N", "Q", "R", "W"}),
    "gtfs-l": frozenset({"L"}),
    "gtfs-si": frozenset({"SI"}),
}

BytesFetcher = Callable[[str, int], bytes]


def default_fetcher(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "mta-board/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def feeds_for_routes(routes: tuple[str, ...]) -> tuple[str, ...]:
    unknown = set(routes)
    feeds: list[str] = []
    for feed, feed_routes in FEED_ROUTES.items():
        if unknown & feed_routes:
            feeds.append(feed)
            unknown -= feed_routes
    if unknown:
        raise ValueError(f"unsupported route(s): {', '.join(sorted(unknown))}")
    return tuple(feeds)


class StopCatalog:
    def __init__(
        self,
        cache_dir: Path | None = None,
        fetcher: BytesFetcher = default_fetcher,
    ) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "mta-board"
        self.fetcher = fetcher

    @property
    def cache_file(self) -> Path:
        return self.cache_dir / "stops.json"

    def load(self, timeout: int = 10, max_age_days: int = 7) -> dict[str, str]:
        if self.cache_file.exists():
            age = time.time() - self.cache_file.stat().st_mtime
            if age < max_age_days * 86400:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))

        try:
            payload = self.fetcher(STATIC_GTFS_URL, timeout)
        except Exception:
            if self.cache_file.exists():
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            raise
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            with archive.open("stops.txt") as raw:
                rows = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))
                stops = {row["stop_id"]: row["stop_name"] for row in rows}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(stops, sort_keys=True), encoding="utf-8")
        temporary.replace(self.cache_file)
        return stops


def stop_name(stops: dict[str, str], stop_id: str) -> str:
    if stop_id in stops:
        return stops[stop_id]
    base = stop_id[:-1] if stop_id[-1:] in {"N", "S"} else stop_id
    return stops.get(base, stop_id)


def parse_arrivals(
    payloads: list[bytes],
    config: AppConfig,
    stops: dict[str, str],
    now: datetime | None = None,
) -> tuple[Arrival, ...]:
    current = now or datetime.now(timezone.utc)
    earliest = current + timedelta(minutes=config.board.minimum_lead_minutes)
    target_stop = f"{config.board.station_id}{config.board.direction}"
    wanted_routes = set(config.board.routes)
    found: dict[tuple[str, int], Arrival] = {}

    for payload in payloads:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(payload)
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            update = entity.trip_update
            route = update.trip.route_id.upper()
            if route not in wanted_routes:
                continue
            matching = next((item for item in update.stop_time_update if item.stop_id == target_stop), None)
            if matching is None:
                continue
            timestamp = matching.arrival.time or matching.departure.time
            if not timestamp:
                continue
            arrival_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            if arrival_time < earliest:
                continue
            final_stop = next(
                (item.stop_id for item in reversed(update.stop_time_update) if item.stop_id),
                target_stop,
            )
            arrival = Arrival(
                route=route,
                destination=stop_name(stops, final_stop),
                arrival_time=arrival_time,
                trip_id=update.trip.trip_id,
            )
            found[(arrival.trip_id or entity.id, timestamp)] = arrival

    return tuple(
        sorted(found.values(), key=lambda arrival: arrival.arrival_time)[: config.board.max_arrivals]
    )


def fetch_arrivals(
    config: AppConfig,
    stops: dict[str, str],
    fetcher: BytesFetcher = default_fetcher,
    now: datetime | None = None,
) -> tuple[Arrival, ...]:
    payloads = [
        fetcher(f"{REALTIME_BASE}{feed}", config.network.request_timeout_seconds)
        for feed in feeds_for_routes(config.board.routes)
    ]
    return parse_arrivals(payloads, config, stops, now=now)
