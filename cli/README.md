# MTA Board CLI

The `mta-board` command configures the board, searches MTA stations and routes, tests the live feed, runs the browser preview, creates PNG snapshots, and drives the physical matrix. Its Python implementation is kept separately in [`mta_board_cli`](../src/mta_board_cli/).

## Install

Python 3.11 or newer is required. Run these commands from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run `mta-board COMMAND --help` to see every option for a command.

## Commands

| Command | Purpose | Example |
| --- | --- | --- |
| `stations` | Search stations by name, ID, borough, route, or direction | `mta-board stations "59 lex 6"` |
| `lines` | Search routes and their MTA corridors | `mta-board lines Lexington` |
| `configure` | Show or persist the board configuration | `mta-board configure --station 127 --routes 1,2,3 --direction N` |
| `preview` | Run the live browser preview | `mta-board preview --station 127 --routes 1,2,3 --direction N` |
| `snapshot` | Save one 128×32 PNG frame | `mta-board snapshot --demo --output preview.png` |
| `check` | Verify access to the live MTA feed | `mta-board check --station 127 --routes 1,2,3 --direction N` |
| `run` | Drive the physical HUB75 matrix | `sudo mta-board run --renderer matrix` |

Commands use `config.toml` by default. Pass `--config PATH` to `configure`, `preview`, `snapshot`, `check`, or `run` to use a different file.

## Find a station or route

The bundled catalog includes all current MTA subway and Staten Island Railway station records. Search by station name, borough, corridor, route, direction label, or ID:

```sh
mta-board stations "times sq"
mta-board stations "times sq 2 3"
mta-board stations manhattan N
mta-board stations 6
mta-board lines N
mta-board lines Lexington
```

Results show the GTFS station ID, served routes, and rider-facing meaning of each direction. Ambiguous searches print the possible matches instead of silently choosing one.

`N` and `S` are internal GTFS direction codes, not necessarily geographic north and south. The search results translate them into labels such as Uptown, Downtown, Queens, Manhattan, or Westbound.

## Configure the board

Show the current setup or update it using a station ID or unique search:

```sh
mta-board configure
mta-board configure --station 127 --routes 1,2,3 --direction N
```

This writes `config.toml`. You can also edit the file directly; station IDs must omit the direction suffix:

```toml
[board]
station_id = "127"
routes = ["1", "2", "3"]
direction = "N"
minimum_lead_minutes = 0
max_arrivals = 2
```

Long text scrolls by default. Persistently change that behavior with `mta-board configure --no-scroll` or `mta-board configure --scroll`.

## Preview and snapshots

Start the browser preview with the saved configuration:

```sh
mta-board preview
```

If a preview is already running on that address, the command opens the existing board instead of starting a duplicate server.

Flags on `preview` temporarily override the saved setup:

```sh
mta-board preview --station 127 --routes 1,2,3 --direction N --minimum-lead 5
```

Use deterministic sample arrivals when working offline, or render a single raw frame:

```sh
mta-board preview --demo
mta-board snapshot --demo --output preview.png
```

## Check the live feed

Verify that the MTA endpoint is reachable and its response can be parsed:

```sh
mta-board check --station 127 --routes 1,2,3 --direction N
```

An empty but valid feed is healthy because subway service varies by time of day. Add `--require-arrivals` only when matching trains are expected:

```sh
mta-board check --station 127 --routes 1,2,3 --direction N --require-arrivals
```

The command exits unsuccessfully for network, HTTP, or feed-parsing errors, making it suitable for CI health checks.
