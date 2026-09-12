# MTA LED Arrival Board

[![CI](https://github.com/gerin98/mta-board/actions/workflows/ci.yml/badge.svg)](https://github.com/gerin98/mta-board/actions/workflows/ci.yml)

![Times Square 1 and 2 arrival board preview](docs/times-square-preview.png)

A configurable NYC subway arrival board with a pixel-accurate browser preview and an optional 128×32 HUB75 LED matrix output.

The layout shows the station name and next two trains using Adam Bjornson's monospaced Pixel Five font, official route colors, destinations, and countdowns. Live MTA subway data does not require an API key.

The station, routes, travel direction, arrival cutoff, brightness, and scrolling behavior are all configurable. The application selects the appropriate MTA realtime feed automatically.

## Run the virtual board

Python 3.11 or newer is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
mta-board preview
```

The preview opens at <http://127.0.0.1:8000>. See the [CLI guide](cli/README.md) for station lookup, configuration, snapshots, feed checks, demo mode, and the complete command reference.

## Hardware

No hardware is required for the browser preview. The recommended physical build uses two 64×32 panels to create one 128×32 display, giving station names and destinations enough horizontal space while remaining compact.

| Component | Quantity | Why it is needed | Estimated cost |
| --- | ---: | --- | ---: |
| Raspberry Pi Zero 2 W with soldered 40-pin header | 1 | Runs the application, downloads MTA data over Wi-Fi, and controls the display. An original Pi Zero W also works, but is slower. | $20–30 |
| Adafruit RGB Matrix Bonnet | 1 | Connects the Pi's GPIO header to HUB75 panels and provides the required logic-level conversion. | $15 |
| 64×32 HUB75 RGB LED panel, 3 mm pitch | 2 | Chain horizontally to form the 128×32 display. Matching panel models are strongly recommended. | $90 total |
| Regulated 5V 10A power supply | 1 | Provides enough 5V current for both LED panels. A normal Pi USB adapter cannot power the panels safely. | $30 |
| 32GB A2 microSD card | 1 | Stores Raspberry Pi OS and the board software. | $10–15 |
| HUB75 ribbon and panel power cables | 1 set | Carry display data and distribute 5V power to both panels. These often ship with the panels; verify before ordering. | Usually included |
| Frame, M3 hardware, and standoffs | 1 set | Secures the panels, protects exposed contacts, and keeps the electronics ventilated. | $20–50 |

The electronics cost approximately **$165–180**, or **$190–230** for a finished build with mounting hardware. Prices exclude tax and shipping.

The CanaKit may already provide the Pi, microSD card, card reader, case, and Pi power adapter; count those parts toward this list. Verify that its Pi has a soldered 40-pin GPIO header before attaching the Bonnet. Even with the CanaKit, the Bonnet, two panels, and dedicated 5V 10A panel supply cost about **$135**, plus approximately **$20–50** for a frame.

See the [detailed shopping list](SHOPPING_LIST.md) for example parts, cable checks, optional additions, and a smaller one-panel alternative.

## Run the physical board

Assemble the hardware above and use Raspberry Pi OS Lite 32-bit based on Bookworm or newer.

### Prepare the Raspberry Pi

1. Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to write Raspberry Pi OS Lite (32-bit) to the microSD card.
2. In Imager's OS customization screen, set a hostname, username, password, and Wi-Fi network, then enable SSH. A hostname such as `mta-board` makes the Pi easy to find.
3. Insert the card, start the Pi, allow a minute or two for its first boot, and connect from another computer:

   ```sh
   ssh YOUR_USERNAME@mta-board.local
   ```

   Replace `YOUR_USERNAME` with the username selected in Imager. If the hostname does not resolve, use the Pi's IP address instead of `mta-board.local`.

4. On the Pi, install Git, download this repository, and run the installer:

   ```sh
   sudo apt update
   sudo apt install -y git
   git clone https://github.com/gerin98/mta-board.git
   cd mta-board
   sudo ./scripts/install_pi.sh
   ```

The installer adds the OS dependencies, deploys the project to `/opt/mta-board`, builds a pinned version of the upstream matrix driver, installs the systemd service, and starts the board. It preserves an existing `/opt/mta-board/config.toml`, so it is safe to run again when updating the software.

Use `sudo ./scripts/install_pi.sh --no-start` when preparing the Pi before the panels are connected. Use `./scripts/install_pi.sh --dry-run` to print every planned command without changing the system.

After installation, confirm that the service is running:

```sh
sudo systemctl status --no-pager mta-board
```

The physical driver uses:

- 32 panel rows
- 64 panel columns
- Chain length 2
- `adafruit-hat` GPIO mapping
- 25% initial brightness
- GPIO slowdown 0 for the original Pi Zero W

If the panel shows corruption, change `gpio_slowdown` in `config.toml` one step at a time. Do not increase brightness until the display is stable and adequately powered.

### Service and logs

The installer enables the board service at boot automatically.

Inspect logs with:

```sh
sudo journalctl -u mta-board -f
```

To change a deployed board, SSH into the Pi, update its saved configuration, and restart the service:

```sh
sudo /opt/mta-board/.venv/bin/mta-board configure \
  --config /opt/mta-board/config.toml \
  --station 127 --routes 1,2,3 --direction N
sudo systemctl restart mta-board
```

To install a later version, update the checkout and rerun the same installer:

```sh
cd ~/mta-board
git pull
sudo ./scripts/install_pi.sh
```

The matrix driver requires elevated GPIO access; its upstream runtime initializes the hardware and then drops privileges where supported.

## Tests

```sh
python -m unittest discover -s tests -v
```

The tests use generated GTFS-Realtime fixtures and do not require network access.
