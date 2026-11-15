"""Deadline Desk: urgency plus one study block inside a free calendar gap."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from lib.calendar_ics import Event, gaps

LA_GAP = timedelta(minutes=45)


@dataclass(frozen=True)
class Deadline:
    title: str
    course: str
    due: datetime
    status: str


def load_deadlines(path: Path) -> list[Deadline]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Deadline(
            item["title"],
            item["course"],
            datetime.fromisoformat(item["due"]),
            item["status"],
        )
        for item in raw
    ]


def urgency(item: Deadline, now: datetime) -> str:
    if item.status == "submitted":
        return "submitted"
    if item.due <= now:
        return "overdue"
    if item.due - now <= timedelta(days=3):
        return "due_within_3_days"
    return "later"


def suggest_block(events: list[Event], item: Deadline, now: datetime) -> tuple[datetime, datetime] | None:
    """First free block of at least 45 minutes before the deadline."""
    day = now
    while day.date() <= item.due.date():
        for start, end in gaps(events, day, LA_GAP):
            start = max(start, now)
            if end - start >= LA_GAP and start < item.due:
                return start, end
        day = day + timedelta(days=1)
    return None
