from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import AppConfig, apply_overrides, load_config
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
    return apply_overrides(load_config(args.config), args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
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

