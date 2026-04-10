import pytest

from tests.conftest import weather_vcr
from src.client_weather import WeatherClient


class TestWeatherClient:
    @weather_vcr.use_cassette("openweather.yaml")
    def test_fetch_returns_current_hourly_daily(self, mocker):
        mocker.patch("src.client_weather.config.get", return_value="test-key")
        client = WeatherClient()
        current, hourly, daily = client.fetch(38.7167, -9.1333)

        assert isinstance(current, dict)
        assert len(hourly) > 0
        assert len(daily) > 0

    def test_missing_api_key_raises(self, mocker):
        mocker.patch("src.client_weather.config.get", return_value=None)

        with pytest.raises(RuntimeError, match="openweather_api_key"):
            WeatherClient()
