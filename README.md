# garmin-bridge

Push notifications, alarms, and calendar events from Linux to a Garmin watch via BLE — no smartphone required.

Built for Garmin Fenix 6 on NixOS/Linux. Protocol ported from [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge).

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

```bash
garmin-bridge notify "Title" "Body"
garmin-bridge alarm set 07:00 --label "Wake up"
garmin-bridge alarm list
garmin-bridge calendar sync --source ~/calendar.ics
```

## Project Structure

```
garmin-ble/
├── flake.nix               # Nix dev shell
├── pyproject.toml           # Poetry config
├── Makefile                 # install, discover
├── config.example.toml      # Config template
├── garmin_bridge/
│   ├── cli.py               # Click CLI
│   └── ble/
│       └── connection.py    # BLE scan + GATT discovery
├── systemd/
└── tests/
```

## License

MIT
