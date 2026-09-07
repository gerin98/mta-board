from __future__ import annotations

import argparse
import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

SUPPORTED_ROUTES = frozenset({
    "1", "2", "3", "4", "5", "6", "6X", "7", "7X", "A", "B", "C", "D", "E",
    "F", "FS", "FX", "G", "GS", "H", "J", "L", "M", "N", "Q", "R", "SI", "W", "Z",
})


@dataclass(frozen=True, slots=True)
class BoardConfig:
    station_id: str = "R05"
    routes: tuple[str, ...] = ("N", "W")
    direction: str = "S"
    minimum_lead_minutes: int = 0
    max_arrivals: int = 3


@dataclass(frozen=True, slots=True)
class NetworkConfig:
    feed_refresh_seconds: int = 30
    stale_after_seconds: int = 90
    request_timeout_seconds: int = 10


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    width: int = 128
    height: int = 32
    brightness: int = 25
    gpio_slowdown: int = 0


@dataclass(frozen=True, slots=True)
class AppConfig:
    board: BoardConfig = BoardConfig()
    network: NetworkConfig = NetworkConfig()
    display: DisplayConfig = DisplayConfig()


def _integer(data: dict, name: str, default: int) -> int:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"config file not found: {config_path}") from exc

    board_data = data.get("board", {})
    network_data = data.get("network", {})
    display_data = data.get("display", {})
    routes = board_data.get("routes", ["N", "W"])
    if not isinstance(routes, list) or not all(isinstance(route, str) for route in routes):
        raise ValueError("routes must be an array of strings")

    config = AppConfig(
        board=BoardConfig(
            station_id=str(board_data.get("station_id", "R05")).upper(),
            routes=tuple(route.upper() for route in routes),
            direction=str(board_data.get("direction", "S")).upper(),
            minimum_lead_minutes=_integer(board_data, "minimum_lead_minutes", 0),
            max_arrivals=_integer(board_data, "max_arrivals", 3),
        ),
        network=NetworkConfig(
            feed_refresh_seconds=_integer(network_data, "feed_refresh_seconds", 30),
            stale_after_seconds=_integer(network_data, "stale_after_seconds", 90),
            request_timeout_seconds=_integer(network_data, "request_timeout_seconds", 10),
        ),
        display=DisplayConfig(
            width=_integer(display_data, "width", 128),
            height=_integer(display_data, "height", 32),
            brightness=_integer(display_data, "brightness", 25),
            gpio_slowdown=_integer(display_data, "gpio_slowdown", 0),
        ),
    )
    validate_config(config)
    return config


def apply_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    board = config.board
    if getattr(args, "station", None):
        board = replace(board, station_id=args.station.upper())
    if getattr(args, "routes", None):
        routes = tuple(route.strip().upper() for route in args.routes.split(",") if route.strip())
        board = replace(board, routes=routes)
    if getattr(args, "direction", None):
        board = replace(board, direction=args.direction.upper())
    if getattr(args, "minimum_lead", None) is not None:
        board = replace(board, minimum_lead_minutes=args.minimum_lead)
    updated = replace(config, board=board)
    validate_config(updated)
    return updated


def validate_config(config: AppConfig) -> None:
    board = config.board
    if not re.fullmatch(r"[A-Z0-9]+", board.station_id) or board.station_id[-1:] in {"N", "S"}:
        raise ValueError("station_id must be a base GTFS ID such as R05, without N/S")
    if board.direction not in {"N", "S"}:
        raise ValueError("direction must be N or S")
    if not board.routes:
        raise ValueError("at least one route is required")
    unknown_routes = set(board.routes) - SUPPORTED_ROUTES
    if unknown_routes:
        raise ValueError(f"unsupported route(s): {', '.join(sorted(unknown_routes))}")
    if board.minimum_lead_minutes < 0:
        raise ValueError("minimum_lead_minutes cannot be negative")
    if not 1 <= board.max_arrivals <= 3:
        raise ValueError("max_arrivals must be between 1 and 3 for the 128x32 layout")
    if config.network.feed_refresh_seconds < 10:
        raise ValueError("feed_refresh_seconds must be at least 10")
    if config.network.stale_after_seconds < config.network.feed_refresh_seconds:
        raise ValueError("stale_after_seconds must be at least one refresh interval")
    if config.network.request_timeout_seconds < 1:
        raise ValueError("request_timeout_seconds must be positive")
    if (config.display.width, config.display.height) != (128, 32):
        raise ValueError("this layout currently requires a 128x32 display")
    if not 1 <= config.display.brightness <= 100:
        raise ValueError("brightness must be between 1 and 100")
    if not 0 <= config.display.gpio_slowdown <= 10:
        raise ValueError("gpio_slowdown must be between 0 and 10")
