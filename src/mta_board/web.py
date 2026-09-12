from __future__ import annotations

import errno
import io
import json
import webbrowser
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPException
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .catalog import resolve_station
from .service import BoardService

PREVIEW_HEADER = "X-MTA-Board-Preview"

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MTA LED Board Preview</title>
  <style>
    :root { color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #101114; color: #eee; }
    main { width: 100%; text-align: center; overflow-x: auto; padding: 2rem 0; }
    h1 { font-size: clamp(1rem, 3vw, 1.5rem); font-weight: 500; margin: 0 0 1.5rem; }
    .case { display: inline-block; padding: 24px; border-radius: 12px; background: #24262b; box-shadow: 0 20px 60px #000a, inset 0 0 0 1px #ffffff12; }
    .screen { display: block; width: 1024px; height: 256px; image-rendering: crisp-edges; image-rendering: pixelated; background: #000; box-shadow: inset 0 0 20px #000; }
    #status { margin: 1rem 0 0; min-height: 1.25em; color: #aeb4bd; font-size: .85rem; }
    .live { color: #67d391; } .stale { color: #ff7b72; }
  </style>
</head>
<body>
  <main>
    <h1>MTA 128×32 virtual LED board</h1>
    <div class="case"><img id="board" class="screen" src="/frame.png" alt="Live subway arrival board"></div>
    <p id="status">Connecting…</p>
  </main>
  <script>
    const board = document.querySelector('#board');
    const status = document.querySelector('#status');
    function refreshFrame() {
      board.src = '/frame.png?t=' + Date.now();
    }
    async function refreshStatus() {
      try {
        const response = await fetch('/api/status', {cache: 'no-store'});
        const data = await response.json();
        status.className = data.live ? 'live' : 'stale';
        const health = data.error ? 'MTA feed unavailable' : (data.stale ? 'data stale' : 'live');
        status.textContent = `${data.station_name} · ${data.direction_label} · ${data.arrival_count} arrivals · ${health}`;
      } catch (_) {
        status.className = 'stale'; status.textContent = 'Preview server unavailable';
      }
    }
    refreshFrame(); setInterval(refreshFrame, 83);
    refreshStatus(); setInterval(refreshStatus, 1000);
  </script>
</body>
</html>"""


def _status_payload(service: BoardService) -> dict:
    state = service.state()
    now = datetime.now(timezone.utc)
    age = state.age_seconds(now)
    stale = age is None or age >= service.config.network.stale_after_seconds
    live = not stale and state.error is None
    try:
        station = resolve_station(state.station_id)
        direction_label = station.south_label if state.direction == "S" else station.north_label
    except ValueError:
        direction_label = "Southbound" if state.direction == "S" else "Northbound"
    return {
        "station_id": state.station_id,
        "station_name": state.station_name,
        "direction": state.direction,
        "direction_label": direction_label or "Last stop",
        "routes": list(state.routes),
        "arrival_count": len(state.arrivals),
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "age_seconds": round(age, 1) if age is not None else None,
        "stale": stale,
        "live": live,
        "error": state.error,
        "arrivals": [
            {
                "route": arrival.route,
                "destination": arrival.destination,
                "arrival_time": arrival.arrival_time.isoformat(),
                "trip_id": arrival.trip_id,
            }
            for arrival in state.arrivals
        ],
    }


def make_handler(service: BoardService) -> type[BaseHTTPRequestHandler]:
    class PreviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/frame.png":
                buffer = io.BytesIO()
                service.frame().save(buffer, format="PNG")
                self._send(buffer.getvalue(), "image/png", no_cache=True)
            elif path == "/api/status":
                self._send(json.dumps(_status_payload(service)).encode(), "application/json", no_cache=True)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _send(self, content: bytes, content_type: str, no_cache: bool = False) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header(PREVIEW_HEADER, "1")
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            if no_cache:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                # The browser may replace an in-flight frame during animation.
                pass

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return PreviewHandler


def _loopback_host(host: str) -> str:
    if host == "0.0.0.0":
        return "127.0.0.1"
    if host == "::":
        return "::1"
    return host


def _preview_url(host: str, port: int) -> str:
    display_host = _loopback_host(host)
    if ":" in display_host and not display_host.startswith("["):
        display_host = f"[{display_host}]"
    return f"http://{display_host}:{port}"


def _is_mta_board_preview(host: str, port: int) -> bool:
    connection = HTTPConnection(_loopback_host(host), port, timeout=1)
    try:
        connection.request("GET", "/api/status")
        response = connection.getresponse()
        content = response.read()
        if response.status != HTTPStatus.OK:
            return False
        if response.getheader(PREVIEW_HEADER) == "1":
            return True
        # Recognize preview servers started before the identifying header was added.
        payload = json.loads(content)
        expected_fields = {
            "station_id",
            "station_name",
            "direction",
            "routes",
            "arrival_count",
            "live",
        }
        return isinstance(payload, dict) and expected_fields.issubset(payload)
    except (HTTPException, json.JSONDecodeError, OSError, UnicodeDecodeError):
        return False
    finally:
        connection.close()


def serve_preview(service: BoardService, host: str, port: int, open_browser: bool = True) -> None:
    url = _preview_url(host, port)
    try:
        server = ThreadingHTTPServer((host, port), make_handler(service))
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE and _is_mta_board_preview(host, port):
            print(f"MTA board preview already running: {url}")
            if open_browser:
                webbrowser.open(url)
            return
        raise

    service.start()
    print(f"MTA board preview: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.stop()
