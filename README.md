# Garmin Bridge

Replace Garmin Connect Mobile on Linux — push weather, alarms, and calendar events to a Garmin watch via BLE. No smartphone required.

Tested on Garmin Fenix 6 Pro. Should work on any Garmin watch using the V2 GFDI protocol (not tested):
Fenix 5+/6/7 series, Forerunner 245/745/945/955, Venu/Venu 2, Instinct 2, Enduro.

## Status

**Weather working.** Connects to watch, completes GFDI handshake, responds to weather requests with live data from OpenWeatherMap.

- [x] BLE scanning, pairing, connect/disconnect
- [x] GFDI protocol stack (COBS encoding, CRC, message framing, V2 transport)
- [x] Connection handshake (device info, configuration, time sync)
- [x] Weather — current, hourly (12h), daily (5 day)
- [ ] Alarms
- [ ] Calendar events
- [ ] Daemon mode (long-running connection)

## Requirements

- Linux with BlueZ
- Python 3.11+
- Nix (optional, for dev shell)
- OpenWeatherMap API key (free tier, 2.5 API)

## Setup

```bash
# With Nix
nix develop
make install

# Without Nix
poetry install
```

Add your OpenWeatherMap API key to `config.yaml`:

```yaml
integrations:
  openweather_api_key: your-key-here
```

## Usage

```bash
# Scan and pair a Garmin device
bin/garmin-bridge scan

# Test weather sync (connect, handshake, wait for watch to request weather)
bin/garmin-bridge test weather

# With debug logging
bin/garmin-bridge --debug test weather --timeout 60

# Dump BLE services
bin/garmin-bridge test services
```

Put your watch in pairing mode first (only needed once):
**Settings → Sensors & Accessories → Phone → Pair Phone**

## Tests

```bash
make test
```

## Acknowledgments

This project would not be possible without [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge) — an open-source Android app that replaces proprietary companion apps for smartwatches and fitness trackers. The entire Garmin BLE/GFDI protocol used here was reverse-engineered by the Gadgetbridge community.

## License

MIT
