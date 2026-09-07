from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from importlib.resources import files

BOROUGH_NAMES = {
    "B": "Brooklyn",
    "Bk": "Brooklyn",
    "Bx": "Bronx",
    "M": "Manhattan",
    "Q": "Queens",
    "SI": "Staten Island",
}
ROUTE_TOKENS = frozenset({
    "1", "2", "3", "4", "5", "6", "7", "A", "B", "C", "D", "E", "F", "G", "J", "L",
    "M", "N", "Q", "R", "S", "W", "Z", "SIR",
})


@dataclass(frozen=True, slots=True)
class Station:
    id: str
    name: str
    borough: str
    line: str
    routes: tuple[str, ...]
    latitude: float
    longitude: float
    north_label: str
    south_label: str

    @property
    def borough_name(self) -> str:
        return BOROUGH_NAMES.get(self.borough, self.borough)

    def as_dict(self) -> dict:
        result = asdict(self)
        result["routes"] = list(self.routes)
        result["borough_name"] = self.borough_name
        return result


@dataclass(frozen=True, slots=True)
class LineInfo:
    route: str
    station_count: int
    corridors: tuple[str, ...]


def load_catalog() -> tuple[Station, ...]:
    resource = files("mta_board").joinpath("data/stations.json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    return tuple(
        Station(
            id=item["id"],
            name=item["name"],
            borough=item["borough"],
            line=item["line"],
            routes=tuple(item["routes"]),
            latitude=item["latitude"],
            longitude=item["longitude"],
            north_label=item["north_label"],
            south_label=item["south_label"],
        )
        for item in data["stations"]
    )


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def search_stations(query: str, stations: tuple[Station, ...] | None = None) -> list[Station]:
    catalog = stations or load_catalog()
    normalized = _normalize(query)
    if not normalized:
        return list(catalog)
    terms = normalized.split()

    exact_names = [station for station in catalog if _normalize(station.name) == normalized]
    if exact_names:
        return sorted(exact_names, key=lambda station: (station.name, station.id))

    route_terms = {term.upper() for term in terms} & ROUTE_TOKENS
    text_terms = [term for term in terms if term.upper() not in route_terms]

    def searchable(station: Station) -> str:
        return _normalize(
            " ".join(
                (
                    station.id,
                    station.name,
                    station.borough,
                    station.borough_name,
                    station.line,
                    *station.routes,
                    station.north_label,
                    station.south_label,
                )
            )
        )

    matches = [
        station
        for station in catalog
        if route_terms <= set(station.routes)
        and all(term in searchable(station) for term in text_terms)
    ]
    return sorted(
        matches,
        key=lambda station: (
            station.id.casefold() != normalized,
            _normalize(station.name) != normalized,
            not _normalize(station.name).startswith(normalized),
            station.name,
            station.id,
        ),
    )


def search_lines(query: str = "", stations: tuple[Station, ...] | None = None) -> list[LineInfo]:
    catalog = stations or load_catalog()
    by_route: dict[str, list[Station]] = {}
    for station in catalog:
        for route in station.routes:
            by_route.setdefault(route, []).append(station)

    normalized = _normalize(query)
    exact_route = normalized.upper() if normalized.upper() in by_route else None
    results: list[LineInfo] = []
    for route, route_stations in by_route.items():
        corridors = tuple(sorted({station.line for station in route_stations}))
        searchable = _normalize(" ".join((route, *corridors)))
        if exact_route and route != exact_route:
            continue
        if not exact_route and normalized and normalized not in searchable:
            continue
        results.append(LineInfo(route, len(route_stations), corridors))

    return sorted(
        results,
        key=lambda line: (not line.route.isdigit(), int(line.route) if line.route.isdigit() else line.route),
    )


def resolve_station(value: str) -> Station:
    matches = search_stations(value)
    exact_ids = [station for station in matches if station.id.casefold() == value.casefold()]
    if exact_ids:
        return exact_ids[0]
    exact_names = [station for station in matches if _normalize(station.name) == _normalize(value)]
    if len(exact_names) == 1:
        return exact_names[0]
    if len(matches) == 1:
        return matches[0]
    query_terms = {term.upper() for term in _normalize(value).split()}
    route_terms = query_terms & ROUTE_TOKENS
    route_matches = [station for station in matches if route_terms and route_terms <= set(station.routes)]
    if len(route_matches) == 1:
        return route_matches[0]
    if not matches:
        raise ValueError(f"no MTA station matches {value!r}; run 'mta-board stations SEARCH'")
    suggestions = ", ".join(f"{station.id} ({station.name}, {station.line})" for station in matches[:5])
    raise ValueError(f"station search {value!r} is ambiguous: {suggestions}")


def bundled_stop_names() -> dict[str, str]:
    return {station.id: station.name for station in load_catalog()}
