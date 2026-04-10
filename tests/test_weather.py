import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.weather import handle_request, Condition, _garmin_condition
from src.protocol import MessageType


FAKE_CURRENT = {
    "temp":         22.5,
    "feels_like":   21.0,
    "humidity":     65,
    "temp_min":     20.0,
    "temp_max":     24.0,
    "wind_speed":   4.5,
    "wind_deg":     220,
    "condition_id": 800,
    "location":     "Lisbon",
    "timestamp":    1712764800,
    "pop":          0,
}

FAKE_HOURLY = [
    {
        "temp": 20.0, "feels_like": 19.0, "humidity": 70, "wind_speed": 3.0,
        "wind_deg": 200, "condition_id": 802, "pop": 0.1, "timestamp": 1712768400,
    },
    {
        "temp": 18.0, "feels_like": 17.0, "humidity": 75, "wind_speed": 2.5,
        "wind_deg": 190, "condition_id": 500, "pop": 0.4, "timestamp": 1712772000,
    },
]

FAKE_DAILY = [
    {"temp_max": 24.0, "temp_min": 15.0, "condition_id": 800, "pop": 0.1, "timestamp": 1712750400},
    {"temp_max": 22.0, "temp_min": 14.0, "condition_id": 501, "pop": 0.6, "timestamp": 1712836800},
]


def _valid_payload(hours=12):
    """Build a minimal valid WEATHER_REQUEST payload (10 bytes)."""
    return bytes(9) + bytes([hours])


def _mock_clients(mock_location_class, mock_weather_class):
    mock_location = MagicMock()
    mock_location.fetch.return_value = (38.72, -9.13)
    mock_location_class.return_value = mock_location

    mock_weather = MagicMock()
    mock_weather.fetch.return_value = (FAKE_CURRENT, FAKE_HOURLY, FAKE_DAILY)
    mock_weather_class.return_value = mock_weather


def _run_handler(protocol, payload=None):
    handle_request(protocol, MessageType.WEATHER_REQUEST, payload or _valid_payload())
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))


# --- handle_request ---

def test_ignores_short_payload():
    protocol = MagicMock()
    handle_request(protocol, MessageType.WEATHER_REQUEST, bytes(5))
    protocol.send.assert_not_called()


@patch("src.weather.WeatherClient")
@patch("src.weather.LocationClient")
def test_sends_definition_and_data(mock_location_class, mock_weather_class):
    _mock_clients(mock_location_class, mock_weather_class)

    protocol         = MagicMock()
    protocol.send    = AsyncMock()
    protocol.respond = AsyncMock()

    _run_handler(protocol)

    assert protocol.send.call_count == 2
    assert protocol.respond.call_count == 1

    definition_call = protocol.send.call_args_list[0]
    data_call       = protocol.send.call_args_list[1]

    assert definition_call[0][0] == MessageType.FIT_DEFINITION
    assert data_call[0][0] == MessageType.FIT_DATA
    assert len(definition_call[0][1]) > 0
    assert len(data_call[0][1]) > 0


@patch("src.weather.WeatherClient")
@patch("src.weather.LocationClient")
def test_responds_on_error(mock_location_class, mock_weather_class):
    mock_location = MagicMock()
    mock_location.fetch.side_effect = RuntimeError("no network")
    mock_location_class.return_value = mock_location

    protocol         = MagicMock()
    protocol.send    = AsyncMock()
    protocol.respond = AsyncMock()

    _run_handler(protocol)

    protocol.send.assert_not_called()
    protocol.respond.assert_called_once()


# --- condition mapping ---

@pytest.mark.parametrize("owm_id, expected", [
    (800, Condition.CLEAR),
    (211, Condition.THUNDERSTORMS),
    (500, Condition.LIGHT_RAIN),
    (601, Condition.SNOW),
    (741, Condition.FOG),
    (803, Condition.MOSTLY_CLOUDY),
    (999, Condition.CLEAR),  # unknown defaults to CLEAR
])
def test_garmin_condition_mapping(owm_id, expected):
    assert _garmin_condition(owm_id) == expected
