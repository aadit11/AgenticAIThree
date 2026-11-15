# Process log

## AI tools used

- Cursor, Grok 4.7, on 14 November 2026.

## Attribution

- `lib/calendar_ics.py`, `lib/email_gate.py`, `lib/deadlines.py`, `lib/search_tool.py`, `router/router.py`, and the skill CLIs were drafted in Cursor. The approval rules follow `plan.md`: exact `APPROVE <draft-id>`, owner id, recipient allowlist, and cron cannot send.
- Checked with `python -m unittest` for the calendar fixture, the send gate, deadline labels, untrusted search snippets, and every router reason. No live mailbox send was made.
