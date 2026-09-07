from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Arrival:
    route: str
    destination: str
    arrival_time: datetime
    trip_id: str = ""

    @property
    def timestamp(self) -> int:
        return int(self.arrival_time.timestamp())


@dataclass(frozen=True, slots=True)
class BoardState:
    station_id: str
    station_name: str
    direction: str
    routes: tuple[str, ...]
    arrivals: tuple[Arrival, ...] = field(default_factory=tuple)
    updated_at: datetime | None = None
    error: str | None = None

    def age_seconds(self, now: datetime | None = None) -> float | None:
        if self.updated_at is None:
            return None
        current = now or datetime.now(timezone.utc)
        return max(0.0, (current - self.updated_at).total_seconds())

