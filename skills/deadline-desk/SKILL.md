---
name: deadline-desk
description: Rank deadlines and suggest one open study block.
version: 0.1.0
author: Lumen
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deadlines, lumen]
    requires_toolsets: [terminal]
---

# Deadline Desk

Compare `synthetic/deadlines.json` with the calendar. Label each item submitted, overdue, due within 3 days, or later. Suggest one free block of at least 45 minutes before an open deadline.

## When to Use

- The user asks what is due, or a briefing needs the deadline line.
- A proactive alert checks for an item due within 3 days.

## How to Run

```
python skills/deadline-desk/scripts/deadline_tool.py --now 2026-11-14T18:00:00-08:00
```

Omit `--now` to use the current time. This skill does not send email.
