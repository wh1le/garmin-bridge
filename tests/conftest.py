import json
import os

import vcr

CASSETTES_DIR = os.path.join(os.path.dirname(__file__), "cassettes")

# Default: block all network requests. Set VCR_RECORD=1 to re-record cassettes.
RECORD_MODE = "once" if os.environ.get("VCR_RECORD") else "none"

SENSITIVE_LOCATION_FIELDS = {
    "query": "FILTERED",
    "isp":   "FILTERED",
    "org":   "FILTERED",
    "as":    "FILTERED",
    "zip":   "FILTERED",
    "lat":   0.0,
    "lon":   0.0,
}


def _scrub_location_response(response):
    """Remove IP, ISP, and other identifying info from ip-api responses."""
    try:
        body = json.loads(response["body"]["string"])
        for field, replacement in SENSITIVE_LOCATION_FIELDS.items():
            if field in body:
                body[field] = replacement
        response["body"]["string"] = json.dumps(body).encode()
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return response


def _scrub_weather_response(response):
    """Remove coordinates echoed back in OWM responses."""
    try:
        body = json.loads(response["body"]["string"])
        if "coord" in body:
            body["coord"] = {}
        if "city" in body and "coord" in body["city"]:
            body["city"]["coord"] = {}
        response["body"]["string"] = json.dumps(body).encode()
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return response


weather_vcr = vcr.VCR(
    cassette_library_dir    = CASSETTES_DIR,
    record_mode             = RECORD_MODE,
    filter_query_parameters = [("appid", "FILTERED"), ("lat", "0"), ("lon", "0")],
    before_record_response  = _scrub_weather_response,
)

location_vcr = vcr.VCR(
    cassette_library_dir   = CASSETTES_DIR,
    record_mode            = "once",
    before_record_response = _scrub_location_response,
)
