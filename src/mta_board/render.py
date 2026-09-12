from __future__ import annotations

from datetime import datetime, timezone

from PIL import Image, ImageDraw

from .catalog import Station, resolve_station
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

# Brighter than the MTA's dark signage blue so it remains legible on a matrix
# running at low indoor brightness.
STATION_COLOR = (0, 170, 255)
LINE_COLOR = (170, 220, 255)

HEADER_ABBREVIATIONS = {
    "BROADWAY": "BDWY",
    "DOWNTOWN": "DTWN",
    "LEXINGTON": "LEX",
    "PLAZA": "PLZ",
    "QUEENSBORO": "QNSBORO",
    "UPTOWN": "UPTWN",
}
SCROLL_PIXELS_PER_SECOND = 12
SCROLL_START_PAUSE_SECONDS = 5
SCROLL_END_PAUSE_SECONDS = 2
HEADER_GAP = 4
DESTINATION_X = 13
COUNTDOWN_LEFT_GAP = 4
ROUTE_BULLET = (
    "001111100",
    "011111110",
    "111111111",
    "111111111",
    "111111111",
    "111111111",
    "111111111",
    "011111110",
    "001111100",
)
ROUTE_PILL = (
    "00111111100",
    "01111111110",
    "11111111111",
    "11111111111",
    "11111111111",
    "11111111111",
    "11111111111",
    "01111111110",
    "00111111100",
)

# Bitmap glyphs derived from Adam Bjornson's monospaced Pixel Five font, used
# under its MIT-style license. Each glyph occupies a fixed 5x5 cell with one
# pixel of letter spacing. Storing the native-resolution bitmaps keeps rendering
# crisp and identical across Pillow and FreeType versions.
# https://bitfume.com/tools/fonts/pixel-five/
GLYPHS: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 5,
    "-": ("00000", "00000", "01110", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00100"),
    "/": ("00001", "00010", "00100", "01000", "10000"),
    "0": ("01110", "10011", "10101", "11001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00110", "01000", "11111"),
    "3": ("11110", "00001", "00110", "00001", "11110"),
    "4": ("10010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "11110"),
    "6": ("01111", "10000", "11110", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000"),
    "8": ("01110", "10001", "01110", "10001", "01110"),
    "9": ("11111", "10001", "11111", "00001", "11110"),
    "A": ("00100", "01010", "01110", "10001", "10001"),
    "B": ("11100", "10010", "11110", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "11100", "10000", "11111"),
    "F": ("11111", "10000", "11100", "10000", "10000"),
    "G": ("01111", "10000", "10111", "10001", "01111"),
    "H": ("10001", "10001", "11111", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "11111"),
    "J": ("01111", "00010", "00010", "10010", "01100"),
    "K": ("10010", "10100", "11100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "11110", "10000", "10000"),
    "Q": ("01110", "10001", "10101", "10011", "01111"),
    "R": ("11110", "10001", "11110", "10110", "10001"),
    "S": ("01111", "10000", "01110", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10101", "10101", "01010"),
    "X": ("10001", "01010", "00100", "01010", "10001"),
    "Y": ("10001", "10001", "01111", "00001", "01110"),
    "Z": ("11111", "00010", "00100", "01000", "11111"),
}


def _glyph_advance(character: str) -> int:
    # A full monospaced space creates a six-pixel hole on this tiny display.
    # Two pixels of advance plus the previous glyph's trailing column produces
    # a more readable three-pixel gap between words.
    return 2 if character == " " else 6


def _text_width(text: str) -> int:
    if not text:
        return 0
    text = text.upper()
    return sum(_glyph_advance(character) for character in text[:-1]) + 5


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
    glyph_x = start_x
    for character in text.upper():
        glyph = GLYPHS.get(character, GLYPHS[" "])
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((glyph_x + column_index, start_y + row_index), fill=fill)
        glyph_x += _glyph_advance(character)


def _scroll_offset(
    now: datetime,
    started_at: datetime,
    overflow_width: int,
    synchronized_overflow_width: int | None = None,
) -> int:
    synchronized_width = synchronized_overflow_width or overflow_width
    travel_seconds = synchronized_width / SCROLL_PIXELS_PER_SECOND
    cycle_seconds = SCROLL_START_PAUSE_SECONDS + travel_seconds + SCROLL_END_PAUSE_SECONDS
    elapsed = max(0.0, (now - started_at).total_seconds()) % cycle_seconds
    if elapsed <= SCROLL_START_PAUSE_SECONDS:
        return 0
    travel_elapsed = elapsed - SCROLL_START_PAUSE_SECONDS
    if travel_elapsed >= travel_seconds:
        return overflow_width
    return min(overflow_width, int(travel_elapsed * SCROLL_PIXELS_PER_SECOND))


def _paste_text_strip(
    image: Image.Image,
    strip: Image.Image,
    position: tuple[int, int],
    viewport_width: int,
    now: datetime,
    started_at: datetime,
    synchronized_overflow_width: int,
    scrolling: bool,
    center_when_static: bool = False,
) -> None:
    if viewport_width <= 0:
        return
    viewport = Image.new("RGB", (viewport_width, strip.height), (0, 0, 0))
    if strip.width <= viewport_width or not scrolling:
        x = (viewport_width - strip.width) // 2 if center_when_static else 0
        viewport.paste(strip.crop((0, 0, viewport_width, strip.height)), (max(0, x), 0))
    else:
        overflow_width = strip.width - viewport_width
        offset = _scroll_offset(
            now,
            started_at,
            overflow_width,
            synchronized_overflow_width,
        )
        viewport = strip.crop((offset, 0, offset + viewport_width, strip.height))
    image.paste(viewport, position)


def _text_strip(text: str, fill: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (max(1, _text_width(text)), 5), (0, 0, 0))
    _draw_text(ImageDraw.Draw(strip), (0, 0), text, fill)
    return strip


def _countdown(arrival: Arrival, now: datetime) -> str:
    seconds = max(0, int((arrival.arrival_time - now).total_seconds()))
    if seconds < 60:
        return "DUE"
    return f"{seconds // 60} min"


def _route_text_color(route: str) -> tuple[int, int, int]:
    return (0, 0, 0) if route in {"N", "Q", "R", "W"} else (255, 255, 255)


def _draw_route_bullet(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    fill: tuple[int, int, int],
    pattern: tuple[str, ...] = ROUTE_BULLET,
) -> None:
    start_x, start_y = position
    for row_index, row in enumerate(pattern):
        for column_index, pixel in enumerate(row):
            if pixel == "1":
                draw.point((start_x + column_index, start_y + row_index), fill=fill)


def _abbreviate_header(text: str) -> str:
    return " ".join(HEADER_ABBREVIATIONS.get(word, word) for word in text.upper().split())


def _station_identity(station: Station) -> str:
    return station.name.upper()


def _header_parts(station: Station, direction: str, width: int) -> tuple[str, str]:
    station_text = _station_identity(station)
    direction_text = station.north_label if direction == "N" else station.south_label
    direction_text = (direction_text or direction).upper()
    gap = HEADER_GAP

    if _text_width(station_text) + gap + _text_width(direction_text) <= width:
        return station_text, direction_text

    station_text = _abbreviate_header(station_text)
    direction_text = _abbreviate_header(direction_text)
    if _text_width(station_text) + gap + _text_width(direction_text) <= width:
        return station_text, direction_text

    station_width = max(0, width - gap - _text_width(direction_text))
    station_text = _fit_text(station_text, station_width)
    if station_text:
        return station_text, direction_text
    return _fit_text(_abbreviate_header(_station_identity(station)), width), ""


def _full_header_parts(station: Station, direction: str) -> tuple[str, str]:
    direction_text = station.north_label if direction == "N" else station.south_label
    return _station_identity(station), (direction_text or direction).upper()


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
    feed_error = state.error is not None
    degraded = feed_error or stale
    visible_rows = min(2, len(arrivals))
    if degraded:
        visible_rows = min(1, visible_rows)

    header_gap = HEADER_GAP
    try:
        station = resolve_station(state.station_id)
        if config.display.scrolling:
            station_name, station_context = _full_header_parts(station, state.direction)
        else:
            station_name, station_context = _header_parts(
                station,
                state.direction,
                config.display.width - 2,
            )
    except ValueError:
        station_name = _fit_text(state.station_name, config.display.width - 2)
        station_context = state.direction
    header_width = _text_width(station_name)
    if station_context:
        header_width += header_gap + _text_width(station_context)
    header_strip = Image.new("RGB", (max(1, header_width), 5), (0, 0, 0))
    header_draw = ImageDraw.Draw(header_strip)
    _draw_text(header_draw, (0, 0), station_name, STATION_COLOR)
    if station_context:
        _draw_text(
            header_draw,
            (_text_width(station_name) + header_gap, 0),
            station_context,
            LINE_COLOR,
        )
    header_viewport_width = config.display.width - 2
    synchronized_overflow_width = max(0, header_strip.width - header_viewport_width)
    for arrival in arrivals[:visible_rows]:
        countdown_x = config.display.width - 1 - _text_width(_countdown(arrival, current))
        destination_width = max(0, countdown_x - DESTINATION_X - COUNTDOWN_LEFT_GAP)
        synchronized_overflow_width = max(
            synchronized_overflow_width,
            _text_width(arrival.destination) - destination_width,
        )
    _paste_text_strip(
        image,
        header_strip,
        (1, 3),
        header_viewport_width,
        current,
        state.updated_at or current,
        synchronized_overflow_width,
        config.display.scrolling,
        center_when_static=True,
    )

    if not arrivals and not degraded:
        message = "NO UPCOMING TRAINS"
        _draw_text(draw, (3, 17), _fit_text(message, 122), (252, 204, 10))
        return image

    for index, arrival in enumerate(arrivals[:visible_rows]):
        # A hand-tuned 9x9 silhouette stays circular on the coarse LED grid.
        y = 10 + index * 11
        color = ROUTE_COLORS.get(arrival.route, (128, 129, 131))
        route_label = arrival.route[:2]
        badge_pattern = ROUTE_BULLET if len(route_label) == 1 else ROUTE_PILL
        badge_width = len(badge_pattern[0])
        _draw_route_bullet(draw, (1, y), color, badge_pattern)
        route_width = _text_width(route_label)
        _draw_text(
            draw,
            (
                1 + (badge_width - route_width) // 2,
                y + 2,
            ),
            route_label,
            _route_text_color(arrival.route),
        )
        countdown = _countdown(arrival, current)
        countdown_width = _text_width(countdown)
        countdown_x = config.display.width - 1 - countdown_width
        destination_width = max(0, countdown_x - DESTINATION_X - COUNTDOWN_LEFT_GAP)
        destination = (
            arrival.destination
            if config.display.scrolling
            else _fit_text(arrival.destination, destination_width)
        )
        _paste_text_strip(
            image,
            _text_strip(destination, (255, 255, 255)),
            (DESTINATION_X, y + 2),
            destination_width,
            current,
            state.updated_at or current,
            synchronized_overflow_width,
            config.display.scrolling,
        )
        _draw_text(draw, (countdown_x, y + 2), countdown, (252, 204, 10))

    if degraded:
        status_y = 21
        if state.updated_at is None:
            status = "MTA OFFLINE"
        elif stale:
            status = "DATA STALE"
        else:
            status = "MTA ERROR"
        draw.rectangle((1, status_y, 126, 30), fill=(70, 0, 0))
        _draw_text(draw, (3, status_y + 2), status, (255, 80, 80))
    return image
