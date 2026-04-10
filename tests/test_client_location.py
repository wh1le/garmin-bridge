from tests.conftest import location_vcr

from src.client_location import LocationClient


class TestLocationClient:
    @location_vcr.use_cassette("location.yaml")
    def test_fetch_returns_coordinates(self):
        client = LocationClient()
        latitude, longitude = client.fetch()

        assert isinstance(latitude, float)
        assert isinstance(longitude, float)

    @location_vcr.use_cassette("location.yaml")
    def test_fetch_returns_plausible_values(self):
        client = LocationClient()
        latitude, longitude = client.fetch()

        assert -90 <= latitude <= 90
        assert -180 <= longitude <= 180
