# garmin-bridge

Push notifications, alarms, and calendar events from Linux to a Garmin watch via BLE — no smartphone required.

Built for Garmin Fenix 6 PRO on Linux.

## Status

**Phase 1: Connect & Discover** — BLE scanning and GATT service enumeration working. Notification protocol not yet implemented.

## Requirements

- Linux with BlueZ
- Python 3.11+
- Nix (optional, for dev shell)

## Setup

```bash
# With Nix
nix develop
make install

# Without Nix
poetry install
```

## Usage

```bash
# Scan for Garmin devices and dump BLE services
make discover

# Or directly
garmin-bridge discover
garmin-bridge discover --timeout 15
```

Put your watch in pairing mode first: **Settings → Sensors & Accessories → Phone → Pair Phone**

## Planned Commands

1. Calendar events — push events, watch shows/alerts
2. Weather — respond when watch asks
3. Waypoints — upload locations for navigation

```bash

garmin-bridge alarm set 07:00 --label "Wake up"
garmin-bridge alarm list
garmin-bridge calendar sync --source ~/calendar.ics
```

## Acknowledgments

This project would not be possible without [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge) — an open-source Android app that replaces proprietary companion apps for smartwatches and fitness trackers. The entire Garmin BLE/GFDI protocol used here was reverse-engineered by the Gadgetbridge community. Their work on Garmin device support (Fenix 6 added in v0.88.0) is the foundation this project builds on.

## License

MIT
