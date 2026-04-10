"""ICS calendar client.

Fetches events from any public ICS/CalDAV URL.
Returns plain dicts — no Garmin knowledge.
"""

import urllib.request
from datetime import datetime, timezone

from icalendar import Calendar

from src.config import config
from src.logger import log


class CalendarClient:
    def __init__(self):
        self.urls = config.get("calendar.urls", [])
        if not self.urls:
            single_url = config.get("calendar.url", "")
            if single_url:
                self.urls = [single_url]
            else:
                raise RuntimeError("Missing calendar.urls in config")

    def fetch(self, start, end):
        """Fetch events from all calendars between start and end (unix timestamps).

        Returns sorted list of dicts with: title, location, description,
        organizer, start_date, end_date, all_day.
        """
        all_events = []
        for url in self.urls:
            all_events.extend(self._fetch_one(url, start, end))

        all_events.sort(key=lambda event: event["start_date"])
        log.info("Found %d events total from %d calendars", len(all_events), len(self.urls))
        return all_events

    def _fetch_one(self, url, start, end):
        """Fetch events from a single ICS URL."""
        log.info("Fetching calendar from %s", url)

        with urllib.request.urlopen(url, timeout=15) as response:
            raw = response.read()

        return [
            event for component in Calendar.from_ical(raw).walk()
            if component.name == "VEVENT"
            and (event := _parse_event(component)) is not None
            and event["start_date"] <= end
            and event["end_date"] >= start
        ]


def _parse_event(component):
    """Extract event fields from an icalendar VEVENT component."""
    dtstart = component.get("dtstart")
    if dtstart is None:
        return None

    dtend = component.get("dtend")
    start_dt = dtstart.dt
    end_dt = dtend.dt if dtend else start_dt
    all_day = not isinstance(start_dt, datetime)

    organizer = component.get("organizer")
    if organizer:
        organizer = str(organizer).replace("mailto:", "")

    return {
        "title":       str(component.get("summary", "")),
        "location":    str(component.get("location", "")),
        "description": str(component.get("description", "")),
        "organizer":   organizer or "",
        "start_date":  _to_timestamp(start_dt, all_day),
        "end_date":    _to_timestamp(end_dt, all_day),
        "all_day":     all_day,
    }


def _to_timestamp(dt_value, all_day):
    """Convert a date or datetime to a unix timestamp."""
    if all_day:
        return int(datetime(
            dt_value.year, dt_value.month, dt_value.day,
            tzinfo=timezone.utc,
        ).timestamp())

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)

    return int(dt_value.timestamp())
