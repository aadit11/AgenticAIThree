---
name: lumen-calendar
description: Read the temporary calendar for conflicts and gaps.
version: 0.1.0
author: Lumen
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [calendar, lumen]
    requires_toolsets: [terminal]
---

# Calendar

Read the temporary assignment calendar. Report events, overlapping events, and open gaps of at least 45 minutes. Do not open a personal or USC calendar.

## When to Use

- The user asks what is on today, where a conflict is, or where a study block could fit.
- A morning briefing or deadline plan needs the schedule.

## How to Run

From the repository root:

```
python skills/calendar/scripts/calendar_tool.py
```

Use `--fixture synthetic/fixtures/calendar.ics --day 2026-11-15T08:00:00-08:00` when the live feed is unavailable. The live command reads `CALENDAR_ICS_URL` and must not print that URL.
