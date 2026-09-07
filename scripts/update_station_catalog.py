#!/usr/bin/env python3
"""Download and normalize the official MTA station catalog."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://data.ny.gov/resource/39hk-dx4f.json?%24limit=5000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="read a previously downloaded Socrata JSON file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1] / "src" / "mta_board" / "data" / "stations.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input:
        records = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "mta-board-catalog/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            records = json.load(response)

    stations = []
    for record in records:
        station_id = record.get("gtfs_stop_id", "").strip()
        if not station_id:
            continue
        stations.append(
            {
                "id": station_id,
                "name": record.get("stop_name", "").strip(),
                "borough": record.get("borough", "").strip(),
                "line": record.get("line", "").strip(),
                "routes": record.get("daytime_routes", "").split(),
                "latitude": float(record["gtfs_latitude"]),
                "longitude": float(record["gtfs_longitude"]),
                "north_label": record.get("north_direction_label", "").strip(),
                "south_label": record.get("south_direction_label", "").strip(),
            }
        )
    stations.sort(key=lambda station: (station["name"], station["id"]))
    payload = {
        "source": SOURCE_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(stations),
        "stations": stations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(stations)} stations to {args.output}")


if __name__ == "__main__":
    main()
