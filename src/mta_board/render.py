from __future__ import annotations

from datetime import datetime, timezone

from PIL import Image, ImageDraw

from .config import AppConfig
from .models import Arrival, BoardState

ROUTE_COLORS: dict[str, tuple[int, int, int]] = {
    "1": (238, 53, 46), "2": (238, 53, 46), "3": (238, 53, 46),
    "4": (0, 147, 60), "5": (0, 147, 60), "6": (0, 147, 60), "6X": (0, 147, 60),
    "7": (185, 51, 173), "7X": (185, 51, 173),
    "A": (0, 57, 166), "C": (0, 57, 166), "E": (0, 57, 166),
    "B": (255, 99, 25), "D": (255, 99, 25), "F": (255, 99, 25), "FX": (255, 99, 25), "M": (255, 99, 25),
    "G": (108, 190, 69),
    "J": (153, 102, 51), "Z": (153, 102, 51),
    "L": (167, 169, 172),
    "N": (252, 204, 10), "Q": (252, 204, 10), "R": (252, 204, 10), "W": (252, 204, 10),
    "S": (128, 129, 131), "FS": (128, 129, 131), "GS": (128, 129, 131),
    "SI": (0, 57, 166),
}

# Fixed 5x7 bitmap glyphs keep every character aligned to the LED grid. Using
# Pillow's default font here would allow different Pillow versions to select
# antialiased fonts, which look soft when enlarged in the browser preview.
GLYPHS: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "/": ("00001", "00010", "00100", "00100", "01000", "10000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00001", "00001", "00001", "00001", "10001", "10001", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

MINI_GLYPHS: dict[str, tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"), "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "110"),
    "A": ("010", "101", "111", "101", "101"), "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"), "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"), "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"), "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"), "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"), "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"), "N": ("101", "111", "111", "111", "101"),
    "O": ("010", "101", "101", "101", "010"), "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "111", "011"), "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"), "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"), "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"), "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"), "Z": ("111", "001", "010", "100", "111"),
}


def _text_width(text: str) -> int:
    return max(0, len(text) * 6 - 1)


def _fit_text(text: str, width: int) -> str:
    text = text.upper()
    if _text_width(text) <= width:
        return text
    suffix = "..."
    shortened = text
    while shortened and _text_width(shortened + suffix) > width:
        shortened = shortened[:-1]
    return (shortened.rstrip(" -") + suffix) if shortened else ""


def _draw_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    fill: tuple[int, int, int],
) -> None:
    start_x, start_y = position
    for character_index, character in enumerate(text.upper()):
        glyph = GLYPHS.get(character, GLYPHS[" "])
        glyph_x = start_x + character_index * 6
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((glyph_x + column_index, start_y + row_index), fill=fill)


def _draw_mini_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    fill: tuple[int, int, int],
) -> None:
    start_x, start_y = position
    for character_index, character in enumerate(text.upper()):
        glyph = MINI_GLYPHS.get(character)
        if glyph is None:
            continue
        glyph_x = start_x + character_index * 4
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((glyph_x + column_index, start_y + row_index), fill=fill)


def _countdown(arrival: Arrival, now: datetime) -> str:
    seconds = max(0, int((arrival.arrival_time - now).total_seconds()))
    if seconds < 60:
        return "DUE"
    return f"{seconds // 60} min"


def _route_text_color(route: str) -> tuple[int, int, int]:
    return (0, 0, 0) if route in {"N", "Q", "R", "W"} else (255, 255, 255)


def render_board(
    state: BoardState,
    config: AppConfig,
    now: datetime | None = None,
) -> Image.Image:
    current = now or datetime.now(timezone.utc)
    image = Image.new("RGB", (config.display.width, config.display.height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    arrivals = list(state.arrivals[: config.board.max_arrivals])
    age = state.age_seconds(current)
    stale = age is None or age >= config.network.stale_after_seconds

    if not arrivals and not stale:
        message = "NO UPCOMING TRAINS"
        _draw_text(draw, (3, 12), _fit_text(message, 122), (252, 204, 10))
        return image

    visible_rows = min(3, len(arrivals))
    if stale:
        visible_rows = min(2, visible_rows)

    for index, arrival in enumerate(arrivals[:visible_rows]):
        y = 1 + index * 10
        color = ROUTE_COLORS.get(arrival.route, (128, 129, 131))
        draw.ellipse((1, y, 10, y + 9), fill=color)
        route_label = arrival.route[:2]
        if len(route_label) == 1:
            route_width = _text_width(route_label)
            _draw_text(
                draw,
                (1 + (10 - route_width) // 2, y + 1),
                route_label,
                _route_text_color(arrival.route),
            )
        else:
            route_width = len(route_label) * 4 - 1
            _draw_mini_text(
                draw,
                (1 + (10 - route_width) // 2, y + 2),
                route_label,
                _route_text_color(arrival.route),
            )
        countdown = _countdown(arrival, current)
        countdown_width = _text_width(countdown)
        countdown_x = config.display.width - 1 - countdown_width
        destination_width = max(0, countdown_x - 15)
        destination = _fit_text(arrival.destination, destination_width)
        _draw_text(draw, (13, y + 1), destination, (255, 255, 255))
        _draw_text(draw, (countdown_x, y + 1), countdown, (252, 204, 10))

    if stale:
        status_y = 21
        status = "OFFLINE" if state.updated_at is None else "DATA STALE"
        draw.rectangle((1, status_y, 126, 30), fill=(70, 0, 0))
        _draw_text(draw, (3, status_y + 2), status, (255, 80, 80))
    return image
