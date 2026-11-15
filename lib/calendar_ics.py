"""Read a temporary Google Calendar iCal feed and find conflicts and gaps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

LA = ZoneInfo("America/Los_Angeles")
DAY_START = time(8, 0)
DAY_END = time(21, 0)


@dataclass(frozen=True)
class Event:
    summary: str
    start: datetime
    end: datetime
    all_day: bool = False


def unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_when(value: str, tzid: str | None) -> tuple[datetime, bool]:
    if "T" not in value:
        day = datetime.strptime(value, "%Y%m%d")
        return day.replace(tzinfo=LA), True
    if value.endswith("Z"):
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(LA), False
    zone = ZoneInfo(tzid) if tzid else LA
    parsed = datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=zone)
    return parsed.astimezone(LA), False


def parse_ics(text: str) -> list[Event]:
    events: list[Event] = []
    current: dict[str, str] | None = None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            events.append(_event_from(current))
            current = None
            continue
        if current is None or ":" not in line:
            continue
        left, _, value = line.partition(":")
        name, _, params = left.partition(";")
        current[name] = value
        if name in {"DTSTART", "DTEND"} and "TZID=" in params:
            current[name + "_TZID"] = params.split("TZID=", 1)[1]
    return [item for item in events if item.end > item.start]


def _event_from(fields: dict[str, str]) -> Event:
    start, all_day = _parse_when(fields.get("DTSTART", ""), fields.get("DTSTART_TZID"))
    if "DTEND" in fields:
        end, _ = _parse_when(fields["DTEND"], fields.get("DTEND_TZID"))
    else:
        end = start + timedelta(hours=1)
    return Event(fields.get("SUMMARY", "(no title)"), start, end, all_day)


def events_on(events: list[Event], day: datetime) -> list[Event]:
    local_day = day.astimezone(LA).date()
    timed = [
        item
        for item in events
        if not item.all_day and item.start.astimezone(LA).date() == local_day
    ]
    return sorted(timed, key=lambda item: item.start)


def conflicts(events: list[Event]) -> list[tuple[Event, Event]]:
    ordered = sorted(events, key=lambda item: item.start)
    found: list[tuple[Event, Event]] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if right.start >= left.end:
                break
            if right.start < left.end:
                found.append((left, right))
    return found


def gaps(events: list[Event], day: datetime, minimum: timedelta = timedelta(minutes=45)) -> list[tuple[datetime, datetime]]:
    local = day.astimezone(LA)
    window_start = datetime.combine(local.date(), DAY_START, LA)
    window_end = datetime.combine(local.date(), DAY_END, LA)
    cursor = window_start
    open_slots: list[tuple[datetime, datetime]] = []
    for item in events_on(events, day):
        start = max(item.start.astimezone(LA), window_start)
        end = min(item.end.astimezone(LA), window_end)
        if start - cursor >= minimum and start > cursor:
            open_slots.append((cursor, start))
        if end > cursor:
            cursor = end
    if window_end - cursor >= minimum and window_end > cursor:
        open_slots.append((cursor, window_end))
    return open_slots
