from __future__ import annotations

import time

from .config import AppConfig
from .service import BoardService


def run_matrix(service: BoardService, config: AppConfig) -> None:
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions
    except ImportError as exc:
        raise RuntimeError(
            "rpi-rgb-led-matrix is not installed; use the Pi installation steps in README.md"
        ) from exc

    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 2
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    options.brightness = config.display.brightness
    options.gpio_slowdown = config.display.gpio_slowdown
    matrix = RGBMatrix(options=options)
    service.start()
    try:
        while True:
            matrix.SetImage(service.frame().convert("RGB"))
            time.sleep(1 / 12)
    except KeyboardInterrupt:
        pass
    finally:
        matrix.Clear()
        service.stop()
