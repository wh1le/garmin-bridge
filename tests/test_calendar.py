from src.calendar import _parse_fields, _build_response, _build_event, _extract_calendar_request
from src.protocol import protobuf


def test_parse_fields_extracts_time_range():
    data = protobuf.field_varint(1, 1000) + protobuf.field_varint(2, 2000)
    result = _parse_fields(data)

    assert result["begin"] == 1000
    assert result["end"] == 2000


def test_parse_fields_defaults_when_empty():
    result = _parse_fields(b"")

    assert result["include_title"] is True
    assert result["max_events"] == 16


def test_extract_calendar_request_finds_nested_data():
    inner = protobuf.field_varint(1, 100)
    service = protobuf.field_message(1, inner)
    smart = protobuf.field_message(1, service)

    result = _extract_calendar_request(smart)
    assert result is not None


def test_extract_calendar_request_ignores_other_services():
    other = protobuf.field_message(8, protobuf.field_varint(1, 1))
    assert _extract_calendar_request(other) is None


def test_build_response_empty_events():
    request = _parse_fields(b"")
    result = _build_response([], request)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_build_event_includes_title():
    request = _parse_fields(protobuf.field_bool(4, True))
    event = {"title": "Dentist", "location": "", "description": "",
             "organizer": "", "start_date": 1000, "end_date": 2000, "all_day": False}

    result = _build_event(event, request)
    assert b"Dentist" in result


def test_build_event_truncates_long_title():
    request = _parse_fields(protobuf.field_bool(4, True))
    request["max_title_length"] = 5
    event = {"title": "Very important meeting", "location": "", "description": "",
             "organizer": "", "start_date": 1000, "end_date": 2000, "all_day": False}

    result = _build_event(event, request)
    assert b"Very " in result
    assert b"Very important" not in result
