# Garmin Bridge

Replace Garmin Connect Mobile on Linux — weather, calendar, and todos on your Garmin watch via BLE. No smartphone required.

Tested on Garmin Fenix 6 Pro (firmware 28.02, 4a9440e). Should work on any Garmin watch using the V2 GFDI protocol (not tested):
Fenix 5+/6/7 series, Forerunner 245/745/945/955, Venu/Venu 2, Instinct 2, Enduro.

## Status

- [x] BLE scanning, pairing, connect/disconnect
- [x] GFDI protocol stack (COBS encoding, CRC, message framing, V2 transport)
- [x] Connection handshake (device info, configuration, time sync)
- [x] Weather — current, hourly (12h), daily (5 day) via OpenWeatherMap
- [x] Calendar — sync events from any ICS URL (Google, Outlook, Nextcloud, etc)
- [x] Todos — push task list as notifications with actions (Done, Remind, Dismiss)
- [x] Daemon mode — stay connected, auto-reconnect
- [ ] Favorite locations — push waypoints to watch map
- [ ] Desktop notifications — mirror Linux notifications to watch
- [ ] Alarms

## Requirements

- Linux with BlueZ
- Python 3.11+
- Nix (optional, for dev shell)
- OpenWeatherMap API key (free tier, 2.5 API)

## Setup

```bash
# With pipx (recommended)
pipx install git+https://github.com/wh1le/garmin-bridge.git

# With Nix
nix develop
make install

# From source
poetry install
```

Configure `config.yaml`:

```yaml
integrations:
  openweather_api_key: your-key-here

calendar:
  urls:
    - https://calendar.google.com/calendar/ical/.../basic.ics
    - https://nextcloud.example.com/remote.php/dav/public-calendars/TOKEN?export

todos:
  - "Buy groceries"
  - title: "Call dentist"
    body: "Dr. Silva, +351 123 456"
```

Any ICS URL works — Google Calendar (use secret address from Settings → Integrate calendar), Outlook, Nextcloud, Fastmail, etc. Multiple calendars are merged into one.

## Todos

Todos are pushed to the watch as notifications when connected. Each todo shows up with three actions:

- **Done** — removes the todo from the watch
- **Remind** — removes and re-pushes after 30 minutes
- **Dismiss** — removes from the watch

Todos can be simple strings or have a title + body for extra detail. Actions only work while connected to the daemon.

> Note: todo storage is currently in `config.yaml`. This will move to a standalone file (JSON or plain text) in a future version to support editing from other tools.

## Usage

```bash
# Scan and pair a Garmin device (only needed once)
bin/garmin-bridge scan

# Run as daemon — stays connected, handles all requests, auto-reconnects
bin/garmin-bridge daemon

# Test mode — connect for a limited time then disconnect
bin/garmin-bridge test connect --timeout 30

# With debug logging
bin/garmin-bridge --debug daemon

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
