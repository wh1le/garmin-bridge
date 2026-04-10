"""OpenWeatherMap 2.5 API client.

Two calls cover all three Garmin needs:
  /weather  → current conditions
  /forecast → 3-hour steps for 5 days (used as hourly + aggregated into daily)
"""

import json
import time
import urllib.request
from collections import defaultdict
from urllib.parse import urlencode

from src.config import config
from src.logger import log

OPEN_WEATHER_URL = "https://api.openweathermap.org/data/2.5"

class WeatherClient:

    def __init__(self):
        self.api_key = config.get("integrations.openweather_api_key")
        if not self.api_key:
            raise RuntimeError("Missing integrations.openweather_api_key in config")

    def fetch(self, lat, lon):
        """Returns (current, hourly, daily) — all plain dicts/lists."""
        raw_current = self._request("weather", lat, lon)
        raw_forecast = self._request("forecast", lat, lon)

        current = self._parse_current(raw_current)
        hourly = self._parse_hourly(raw_forecast)
        daily = self._parse_daily(raw_forecast)

        return current, hourly, daily

    def _request(self, path, lat, lon):
        url = self._url(path, lat, lon)
        log.info("Fetching /%s for lat=%.4f lon=%.4f", path, lat, lon)
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read())

    def _url(self, path, lat, lon):
        params = urlencode({
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "appid": self.api_key
        })

        return f"{OPEN_WEATHER_URL}/{path}?{params}"

    def _parse_entry(self, entry):
        """Normalize a single API entry (works for both /weather and /forecast items)."""
        main = entry["main"]
        return {
            "temp": main["temp"],
            "feels_like": main["feels_like"],
            "humidity": main["humidity"],
            "wind_speed": entry["wind"]["speed"],
            "wind_deg": entry["wind"]["deg"],
            "condition_id": entry["weather"][0]["id"],
            "pop": entry.get("pop", 0),
            "timestamp": entry["dt"],
        }

    def _parse_current(self, raw):
        parsed = self._parse_entry(raw)
        parsed["temp_min"] = raw["main"]["temp_min"]
        parsed["temp_max"] = raw["main"]["temp_max"]
        parsed["location"] = raw.get("name", "")
        return parsed

    def _parse_hourly(self, raw):
        return [self._parse_entry(entry) for entry in raw["list"]]

    def _parse_daily(self, raw):
        entries = self._parse_hourly(raw)

        buckets = defaultdict(list)
        for entry in entries:
            day_of_year = time.gmtime(entry["timestamp"]).tm_yday
            buckets[day_of_year].append(entry)

        days = []
        for day_key in sorted(buckets):
            slots = buckets[day_key]
            middle = slots[len(slots) // 2]
            conditions = [slot["condition_id"] for slot in slots]
            most_frequent_condition = max(set(conditions), key=conditions.count)
            days.append({
                "temp_max": max(slot["temp"] for slot in slots),
                "temp_min": min(slot["temp"] for slot in slots),
                "condition_id": most_frequent_condition,
                "pop": max(slot["pop"] for slot in slots),
                "timestamp": middle["timestamp"],
            })
        return days
