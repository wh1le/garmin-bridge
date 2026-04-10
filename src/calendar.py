"""Calendar feature — sync ICS events to watch via protobuf.

Handles PROTOBUF_REQUEST (5043) containing CalendarService requests.
Fetches events from ICS URL, responds with PROTOBUF_RESPONSE (5044).

Protobuf nesting: Smart(1) → CalendarService(1) → CalendarServiceRequest(1)
"""

import asyncio

from src.client_calendar import CalendarClient
from src.logger import log
from src.protocol import MessageType
from src.protocol import protobuf

# Smart proto field numbers
_SMART_CALENDAR_SERVICE = 1
_CALENDAR_REQUEST = 1
_CALENDAR_RESPONSE = 2

# CalendarServiceResponse status
_STATUS_OK = 1


def handle_request(protocol, _msg_type, payload):
    """Handle PROTOBUF_REQUEST that may contain a calendar request.

    Returns True if handled, False if not a calendar request.
    """
    parsed = protobuf.parse_request(payload)
    if parsed is None:
        return False

    request_id, protobuf_data = parsed
    calendar_data = _extract_calendar_request(protobuf_data)

    if calendar_data is None:
        return False

    request = _parse_fields(calendar_data)
    log.info("Calendar request: begin=%d end=%d max_events=%d",
             request["begin"], request["end"], request["max_events"])

    async def _respond():
        events = _fetch_events(request)
        response = _build_response(events, request)
        smart = protobuf.field_message(_SMART_CALENDAR_SERVICE, response)
        payload = protobuf.build_response(request_id, smart)
        await protocol.send(MessageType.PROTOBUF_RESPONSE, payload)
        log.info("Calendar sent: %d events", len(events))

    asyncio.ensure_future(_respond())
    return True


def _fetch_events(request):
    """Fetch and filter events for the requested time range."""
    try:
        client = CalendarClient()
        events = client.fetch(request["begin"], request["end"])
        return events[:request["max_events"]]
    except RuntimeError as error:
        log.warning("Calendar not configured: %s", error)
        return []
    except Exception as error:
        log.error("Calendar failed: %s", error)
        return []


def _extract_calendar_request(data):
    """Drill into Smart → CalendarService → CalendarServiceRequest."""
    calendar_service = protobuf.get_field(data, _SMART_CALENDAR_SERVICE)
    if not isinstance(calendar_service, (bytes, bytearray)):
        return None

    calendar_request = protobuf.get_field(calendar_service, _CALENDAR_REQUEST)
    if not isinstance(calendar_request, (bytes, bytearray)):
        return None

    return calendar_request


_DEFAULT_REQUEST = {
    "begin":                  0,
    "end":                    0,
    "include_organizer":      False,
    "include_title":          True,
    "include_location":       True,
    "include_description":    False,
    "include_start_date":     True,
    "include_end_date":       False,
    "include_all_day":        False,
    "max_organizer_length":   32,
    "max_title_length":       32,
    "max_location_length":    32,
    "max_description_length": 32,
    "max_events":             16,
}

_FIELD_MAP = {
    1:  "begin",
    2:  "end",
    3:  "include_organizer",
    4:  "include_title",
    5:  "include_location",
    6:  "include_description",
    7:  "include_start_date",
    8:  "include_end_date",
    9:  "include_all_day",
    10: "max_organizer_length",
    11: "max_title_length",
    12: "max_location_length",
    13: "max_description_length",
    14: "max_events",
}


def _parse_fields(data):
    """Parse CalendarServiceRequest protobuf fields into a dict."""
    request = dict(_DEFAULT_REQUEST)

    for field_number, value in protobuf.decode_all(data):
        key = _FIELD_MAP.get(field_number)
        if key:
            request[key] = bool(value) if "include_" in key else value

    return request


def _build_response(events, request):
    """Build CalendarService { calendar_response { status=OK, events } }."""
    parts = [protobuf.field_varint(1, _STATUS_OK)]

    for event in events:
        parts.append(protobuf.field_message(2, _build_event(event, request)))

    return protobuf.field_message(_CALENDAR_RESPONSE, b"".join(parts))


def _build_event(event, request):
    """Build a single CalendarEvent protobuf message."""
    parts = []

    if request["include_organizer"] and event["organizer"]:
        parts.append(protobuf.field_string(1, event["organizer"][:request["max_organizer_length"]]))

    if request["include_title"] and event["title"]:
        parts.append(protobuf.field_string(2, event["title"][:request["max_title_length"]]))

    if request["include_location"] and event["location"]:
        parts.append(protobuf.field_string(3, event["location"][:request["max_location_length"]]))

    if request["include_description"] and event["description"]:
        parts.append(protobuf.field_string(4, event["description"][:request["max_description_length"]]))

    if request["include_start_date"]:
        parts.append(protobuf.field_varint(5, event["start_date"]))

    if request["include_end_date"]:
        parts.append(protobuf.field_varint(6, event["end_date"]))

    if request["include_all_day"]:
        parts.append(protobuf.field_bool(7, event["all_day"]))

    return b"".join(parts)
