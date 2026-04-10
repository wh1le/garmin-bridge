"""IP-based geolocation client.

Uses ip-api.com (free, no key) to resolve current coordinates from IP address.
"""

import json
import urllib.request

from src.logger import log

LOCATION_API_URL = "http://ip-api.com/json/"


class LocationClient:
    def fetch(self):
        """Returns (latitude, longitude) based on current IP address."""
        log.info("Fetching location from %s", LOCATION_API_URL)

        with urllib.request.urlopen(LOCATION_API_URL, timeout=10) as response:
            data = json.loads(response.read())

        if data.get("status") != "success":
            raise RuntimeError(f"Geolocation failed: {data.get('message', 'unknown error')}")

        latitude = data["lat"]
        longitude = data["lon"]
        city = data.get("city", "")
        country = data.get("country", "")

        log.info("Located at %s, %s — lat=%.4f lon=%.4f", city, country, latitude, longitude)
        return latitude, longitude
