from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import Station, resolve_station, search_lines, search_stations
from .config import AppConfig, apply_overrides, load_config, save_config
from .matrix import run_matrix
from .service import BoardService
from .web import serve_preview


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config.toml", help="TOML configuration file")
    parser.add_argument("--station", help="base GTFS station ID, e.g. R05")
    parser.add_argument("--routes", help="comma-separated routes, e.g. N,W")
    parser.add_argument("--direction", choices=("N", "S", "n", "s"))
    parser.add_argument("--minimum-lead", type=int, help="hide trains arriving sooner than this")
    parser.add_argument("--demo", action="store_true", help="use deterministic sample arrivals")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mta-board")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stations = subparsers.add_parser("stations", help="search all MTA subway stations")
    stations.add_argument("query", nargs="*", help="name, ID, borough, line, or route")
    stations.add_argument("--limit", type=int, default=25)
    stations.add_argument("--json", action="store_true", help="output machine-readable JSON")

    lines = subparsers.add_parser("lines", help="search subway routes and corridors")
    lines.add_argument("query", nargs="*", help="route, e.g. N, or corridor, e.g. Lexington")

    configure = subparsers.add_parser("configure", help="show or change the saved board setup")
    configure.add_argument("--config", default="config.toml", help="TOML configuration file")
    configure.add_argument("--station", help="station ID or unique station search")
    configure.add_argument("--routes", help="comma-separated routes, e.g. N,W")
    configure.add_argument("--direction", choices=("N", "S", "n", "s"))
    configure.add_argument("--minimum-lead", type=int, help="hide trains arriving sooner than this")

    preview = subparsers.add_parser("preview", help="run the browser-based virtual board")
    _add_common(preview)
    preview.add_argument("--host", default="127.0.0.1")
    preview.add_argument("--port", type=int, default=8000)
    preview.add_argument("--no-open", action="store_true", help="do not open a browser automatically")

    snapshot = subparsers.add_parser("snapshot", help="write one 128x32 PNG frame")
    _add_common(snapshot)
    snapshot.add_argument("--output", default="preview.png")

    run = subparsers.add_parser("run", help="run the physical LED matrix")
    _add_common(run)
    run.add_argument("--renderer", choices=("matrix",), default="matrix")
    return parser


def resolve_config(args: argparse.Namespace) -> AppConfig:
    if getattr(args, "station", None):
        station = resolve_station(args.station)
        args.station = station.id
        if getattr(args, "routes", None):
            requested = (route.strip().upper() for route in args.routes.split(","))
            args.routes = ",".join(_canonical_route(route, station) for route in requested if route)
    return apply_overrides(load_config(args.config), args)


def list_stations(args: argparse.Namespace) -> None:
    query = " ".join(args.query)
    matches = search_stations(query)
    if args.limit < 1:
        raise ValueError("limit must be positive")
    visible = matches[: args.limit]
    if args.json:
        print(json.dumps([station.as_dict() for station in visible], indent=2))
        return
    if not visible:
        print(f"No stations match {query!r}")
        return
    for index, station in enumerate(visible):
        if index:
            print()
        routes = ", ".join(station.routes) or "None listed"
        print(f"{station.id} — {station.name}")
        print(f"  Location:   {station.borough_name} · {station.line}")
        print(f"  Trains:     {routes}")
        print(f"  Direction N: {station.north_label or 'Last stop'}")
        print(f"  Direction S: {station.south_label or 'Last stop'}")
    if len(matches) > len(visible):
        print(f"Showing {len(visible)} of {len(matches)} matches; use --limit to show more.")


def list_lines(args: argparse.Namespace) -> None:
    query = " ".join(args.query)
    matches = search_lines(query)
    if not matches:
        print(f"No subway lines match {query!r}")
        return
    for line in matches:
        corridors = ", ".join(line.corridors)
        print(f"{line.route} — {line.station_count} stations — {corridors}")


def _print_config(config: AppConfig, path: str) -> None:
    station = resolve_station(config.board.station_id)
    direction_label = station.north_label if config.board.direction == "N" else station.south_label
    print(f"Configuration: {path}")
    print(f"  Station:  {station.id} — {station.name}")
    print(f"  Routes:   {', '.join(config.board.routes)}")
    print(f"  Direction {config.board.direction}: {direction_label or 'Last stop'}")
    print(f"  Lead time: {config.board.minimum_lead_minutes} min")


def _canonical_route(route: str, station: Station) -> str:
    if route == "SIR":
        return "SI"
    if route != "S":
        return route
    if station.id.startswith("S") or station.id == "D26":
        return "FS"
    if station.id in {"901", "902"}:
        return "GS"
    if station.id.startswith("H"):
        return "H"
    return route


def configure_board(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    changing = any(
        value is not None
        for value in (args.station, args.routes, args.direction, args.minimum_lead)
    )
    if not changing:
        _print_config(config, args.config)
        return

    station = resolve_station(args.station or config.board.station_id)
    args.station = station.id if args.station else None
    if args.routes:
        requested = (route.strip().upper() for route in args.routes.split(","))
        args.routes = ",".join(_canonical_route(route, station) for route in requested if route)
    updated = apply_overrides(config, args)
    station_routes = {_canonical_route(route, station) for route in station.routes}
    route_bases = {"6X": "6", "7X": "7", "FX": "F"}
    incompatible = {
        route
        for route in updated.board.routes
        if route not in station_routes and route_bases.get(route) not in station_routes
    }
    if incompatible:
        available = ", ".join(station.routes) or "none listed"
        requested = ", ".join(sorted(incompatible))
        raise ValueError(
            f"{station.name} does not serve route(s) {requested}; available routes: {available}"
        )
    save_config(updated, args.config)
    print(f"Updated {args.config}")
    _print_config(updated, args.config)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "stations":
            list_stations(args)
            return 0
        if args.command == "lines":
            list_lines(args)
            return 0
        if args.command == "configure":
            configure_board(args)
            return 0
        config = resolve_config(args)
        service = BoardService(config, demo=args.demo)
        if args.command == "preview":
            serve_preview(service, args.host, args.port, open_browser=not args.no_open)
        elif args.command == "snapshot":
            service.update()
            output = Path(args.output)
            service.frame().save(output, format="PNG")
            print(f"Wrote {output} ({config.display.width}x{config.display.height})")
        elif args.command == "run":
            run_matrix(service, config)
        return 0
    except (RuntimeError, ValueError, OSError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
