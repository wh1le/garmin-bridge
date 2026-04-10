"""Weather feature — proxy between OWM client and Garmin protocol.

Handles WEATHER_REQUEST (5014). Maps OWM condition codes to Garmin,
delegates API calls to client_weather, record building to protocol.serializer.
"""

import asyncio
import time

from src.client_location import LocationClient
from src.client_weather import WeatherClient
from src.logger import log
from src.protocol import MessageType, serializer


# --- Garmin weather constants ---

WEATHER_MSG = 128
WIND_SPEED_SCALE = 298


class Condition:
    CLEAR                  = 0
    PARTLY_CLOUDY          = 1
    MOSTLY_CLOUDY          = 2
    RAIN                   = 3
    SNOW                   = 4
    WINDY                  = 5
    THUNDERSTORMS          = 6
    WINTRY_MIX             = 7
    FOG                    = 8
    HAZY                   = 11
    HAIL                   = 12
    SCATTERED_SHOWERS      = 13
    SCATTERED_THUNDERSTORMS = 14
    UNKNOWN_PRECIPITATION  = 15
    LIGHT_RAIN             = 16
    HEAVY_RAIN             = 17
    LIGHT_SNOW             = 18
    HEAVY_SNOW             = 19
    LIGHT_RAIN_SNOW        = 20
    HEAVY_RAIN_SNOW        = 21
    CLOUDY                 = 22


class Report:
    CURRENT = 0
    HOURLY  = 1
    DAILY   = 2


# --- Public ---

def handle_request(protocol, _msg_type, payload):
    """Handle WEATHER_REQUEST (5014) from watch."""
    if len(payload) < 10:
        log.warning("Weather request too short: %d bytes", len(payload))
        return

    hours = payload[9]
    log.info("Weather request: hours=%d", hours)

    async def _respond():
        try:
            location = LocationClient()
            lat, lon = location.fetch()

            weather = WeatherClient()
            current, hourly, daily = weather.fetch(lat, lon)
            max_hours = min(hours or 12, 12)

            cur_def, cur_rec   = _build_current(current, lat, lon)
            hr_def, hr_rec     = _build_hourly(hourly, max_hours)
            day_def, day_rec   = _build_daily(daily)

            await protocol.send(MessageType.FIT_DEFINITION, cur_def + hr_def + day_def)
            await protocol.send(MessageType.FIT_DATA, cur_rec + hr_rec + day_rec)
            await protocol.respond(MessageType.WEATHER_REQUEST)

            log.info("Weather sent: current + %d hourly + %d daily",
                     min(len(hourly), max_hours), min(len(daily), 5))

        except Exception as error:
            log.error("Weather failed: %s", error)
            await protocol.respond(MessageType.WEATHER_REQUEST)

    asyncio.ensure_future(_respond())


# --- Private ---

# OWM condition ID → Garmin Condition code
_OWM_TO_GARMIN_DICTIONARY = {
    200: Condition.THUNDERSTORMS,
    201: Condition.THUNDERSTORMS,
    202: Condition.THUNDERSTORMS,
    210: Condition.THUNDERSTORMS,
    211: Condition.THUNDERSTORMS,
    212: Condition.THUNDERSTORMS,
    221: Condition.THUNDERSTORMS,
    230: Condition.THUNDERSTORMS,
    231: Condition.THUNDERSTORMS,
    232: Condition.THUNDERSTORMS,
    300: Condition.LIGHT_RAIN,
    301: Condition.RAIN,
    302: Condition.HEAVY_RAIN,
    310: Condition.LIGHT_RAIN,
    311: Condition.RAIN,
    312: Condition.HEAVY_RAIN,
    313: Condition.SCATTERED_SHOWERS,
    314: Condition.HEAVY_RAIN,
    321: Condition.SCATTERED_SHOWERS,
    500: Condition.LIGHT_RAIN,
    501: Condition.RAIN,
    502: Condition.HEAVY_RAIN,
    503: Condition.HEAVY_RAIN,
    504: Condition.HEAVY_RAIN,
    511: Condition.WINTRY_MIX,
    520: Condition.SCATTERED_SHOWERS,
    521: Condition.SCATTERED_SHOWERS,
    522: Condition.HEAVY_RAIN,
    531: Condition.SCATTERED_SHOWERS,
    600: Condition.LIGHT_SNOW,
    601: Condition.SNOW,
    602: Condition.HEAVY_SNOW,
    611: Condition.WINTRY_MIX,
    612: Condition.WINTRY_MIX,
    613: Condition.WINTRY_MIX,
    615: Condition.LIGHT_RAIN_SNOW,
    616: Condition.HEAVY_RAIN_SNOW,
    620: Condition.LIGHT_SNOW,
    621: Condition.SNOW,
    622: Condition.HEAVY_SNOW,
    701: Condition.FOG,
    711: Condition.HAZY,
    721: Condition.HAZY,
    731: Condition.HAZY,
    741: Condition.FOG,
    751: Condition.HAZY,
    761: Condition.HAZY,
    762: Condition.HAZY,
    771: Condition.WINDY,
    781: Condition.WINDY,
    800: Condition.CLEAR,
    801: Condition.PARTLY_CLOUDY,
    802: Condition.PARTLY_CLOUDY,
    803: Condition.MOSTLY_CLOUDY,
    804: Condition.CLOUDY,
}

# Field definitions: (field_number, size, base_type)
_CURRENT_FIELDS = [
    (0, 1, 0x00), (1, 1, 0x01), (2, 1, 0x00), (3, 2, 0x84), (4, 2, 0x84),
    (5, 1, 0x02), (6, 1, 0x01), (7, 1, 0x02), (8, 15, 0x07), (9, 4, 0x86),
    (10, 4, 0x85), (11, 4, 0x85), (12, 1, 0x00), (13, 1, 0x01), (14, 1, 0x01),
    (15, 1, 0x01), (16, 4, 0x88), (17, 1, 0x00), (253, 4, 0x86),
]

_HOURLY_FIELDS = [
    (0, 1, 0x00), (1, 1, 0x01), (2, 1, 0x00), (3, 2, 0x84), (4, 2, 0x84),
    (5, 1, 0x02), (6, 1, 0x01), (7, 1, 0x02), (15, 1, 0x01), (16, 4, 0x88),
    (17, 1, 0x00), (253, 4, 0x86),
]

_DAILY_FIELDS = [
    (0, 1, 0x00), (2, 1, 0x00), (5, 1, 0x02), (12, 1, 0x00),
    (13, 1, 0x01), (14, 1, 0x01), (253, 4, 0x86),
]


def _garmin_condition(owm_id):
    return _OWM_TO_GARMIN_DICTIONARY.get(owm_id, Condition.CLEAR)


def _build_current(current, lat, lon):
    condition = _garmin_condition(current["condition_id"])

    defn = serializer.definition(0, WEATHER_MSG, _CURRENT_FIELDS)
    rec = serializer.data(0, "<bbBHHBbb15sIiibbbbfBI",
        Report.CURRENT,
        serializer.clamp_temperature(current["temp"]),
        condition,
        round(current["wind_deg"]),
        round(current["wind_speed"] * WIND_SPEED_SCALE),
        0,
        serializer.clamp_temperature(current["feels_like"]),
        current["humidity"],
        serializer.pack_string(current["location"], 15),
        serializer.garmin_timestamp(current["timestamp"]),
        serializer.garmin_coordinate(lat),
        serializer.garmin_coordinate(lon),
        time.gmtime(current["timestamp"]).tm_wday,
        serializer.clamp_temperature(current["temp_max"]),
        serializer.clamp_temperature(current["temp_min"]),
        serializer.clamp_temperature(0),
        0.0,
        0xFF,
        serializer.garmin_timestamp(current["timestamp"]),
    )
    return defn, rec


def _build_hourly(hourly, max_hours):
    defn = serializer.definition(1, WEATHER_MSG, _HOURLY_FIELDS)
    records = b""
    for hour in hourly[:max_hours]:
        condition = _garmin_condition(hour["condition_id"])

        records += serializer.data(1, "<bbBHHBbbbfBI",
            Report.HOURLY,
            serializer.clamp_temperature(hour["temp"]),
            condition,
            round(hour["wind_deg"]),
            round(hour["wind_speed"] * WIND_SPEED_SCALE),
            round(hour["pop"] * 100),
            serializer.clamp_temperature(hour["feels_like"]),
            hour["humidity"],
            serializer.clamp_temperature(0),
            0.0,
            0xFF,
            serializer.garmin_timestamp(hour["timestamp"]),
        )
    return defn, records


def _build_daily(daily):
    defn = serializer.definition(2, WEATHER_MSG, _DAILY_FIELDS)
    records = b""
    for day in daily[:5]:
        condition = _garmin_condition(day["condition_id"])

        records += serializer.data(2, "<bBBBbbI",
            Report.DAILY,
            condition,
            round(day["pop"] * 100),
            time.gmtime(day["timestamp"]).tm_wday,
            serializer.clamp_temperature(day["temp_max"]),
            serializer.clamp_temperature(day["temp_min"]),
            serializer.garmin_timestamp(day["timestamp"]),
        )
    return defn, records
