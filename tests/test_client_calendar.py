from datetime import date, datetime, timezone

from icalendar import Event

from tests.conftest import calendar_vcr
from src.client_calendar import CalendarClient, _parse_event, _to_timestamp

PUBLIC_CALENDAR = "https://calendar.google.com/calendar/ical/en.portuguese%23holiday%40group.v.calendar.google.com/public/basic.ics"


# --- CalendarClient.fetch with VCR ---

@calendar_vcr.use_cassette("calendar.yaml")
def test_fetch_returns_events(mocker):
    mocker.patch("src.client_calendar.config.get", return_value=None)
    client = CalendarClient.__new__(CalendarClient)
    client.urls = [PUBLIC_CALENDAR]

    events = client.fetch(0, 9999999999)

    assert isinstance(events, list)
    assert len(events) > 0
    assert "title" in events[0]


# --- _parse_event ---

def test_parse_timed_event():
    event = Event()
    event.add("summary", "Lunch")
    event.add("dtstart", datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc))
    event.add("dtend", datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc))

    result = _parse_event(event)

    assert result["title"] == "Lunch"
    assert result["all_day"] is False
    assert result["end_date"] > result["start_date"]


def test_parse_all_day_event():
    event = Event()
    event.add("summary", "Holiday")
    event.add("dtstart", date(2026, 4, 10))
    event.add("dtend", date(2026, 4, 11))

    result = _parse_event(event)

    assert result["title"] == "Holiday"
    assert result["all_day"] is True


def test_parse_event_without_dtstart_returns_none():
    event = Event()
    event.add("summary", "Broken")

    assert _parse_event(event) is None


def test_parse_event_extracts_organizer():
    event = Event()
    event.add("summary", "Meeting")
    event.add("dtstart", datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc))
    event.add("organizer", "mailto:boss@example.com")

    result = _parse_event(event)
    assert result["organizer"] == "boss@example.com"


# --- _to_timestamp ---

def test_to_timestamp_date():
    result = _to_timestamp(date(2026, 1, 1), all_day=True)
    assert result > 0


def test_to_timestamp_naive_datetime_assumes_utc():
    naive = datetime(2026, 1, 1, 12, 0)
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert _to_timestamp(naive, all_day=False) == _to_timestamp(aware, all_day=False)
