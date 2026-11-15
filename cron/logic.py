"""Pure job decisions. Callers pass data in and get text or alert ids out."""

from __future__ import annotations

from datetime import datetime, timedelta

from lib.deadlines import Deadline, urgency


def open_deadlines(items: list[Deadline], now: datetime, days: int) -> list[Deadline]:
    chosen = []
    for item in items:
        if item.status == "submitted" or item.due <= now:
            continue
        if item.due - now <= timedelta(days=days):
            chosen.append(item)
    return chosen


def briefing_text(
    *,
    day: str,
    events: list[str],
    gaps: list[str],
    forecast: str,
    mail_lines: list[str],
    deadline_lines: list[str],
) -> str:
    parts = [f"Morning briefing for {day}", f"Weather: {forecast}"]
    parts.append("Events: " + ("; ".join(events) if events else "none"))
    parts.append("Gaps: " + ("; ".join(gaps) if gaps else "none"))
    parts.append("Mail: " + ("; ".join(mail_lines) if mail_lines else "none"))
    parts.append("Deadlines: " + ("; ".join(deadline_lines) if deadline_lines else "none due within 7 days"))
    return "\n".join(parts)


def recap_text(
    *,
    day: str,
    journal_lines: list[str],
    pending_drafts: list[str],
    tomorrow_events: list[str],
) -> str:
    parts = [f"End of day {day}"]
    parts.append("Journal: " + ("; ".join(journal_lines) if journal_lines else "nothing recorded"))
    parts.append("Awaiting approval: " + ("; ".join(pending_drafts) if pending_drafts else "none"))
    parts.append("Tomorrow: " + ("; ".join(tomorrow_events) if tomorrow_events else "no events"))
    return "\n".join(parts)


def new_alerts(
    *,
    now: datetime,
    events: list[tuple[str, datetime]],
    deadlines: list[Deadline],
    flagged: list[dict],
    known_ids: set[str],
) -> list[dict]:
    """Return unseen alerts. Each item has an id and one message."""
    found: list[dict] = []
    horizon = now + timedelta(minutes=30)
    for summary, start in events:
        if now <= start <= horizon:
            found.append(
                {
                    "id": f"meeting:{summary}:{start.isoformat()}",
                    "text": f"Alert: {summary} starts at {start.strftime('%H:%M')}.",
                }
            )
    for item in deadlines:
        if urgency(item, now) == "due_within_3_days":
            found.append(
                {
                    "id": f"deadline:{item.title}",
                    "text": f"Alert: {item.title} is due {item.due.strftime('%b %d')}.",
                }
            )
    for message in flagged:
        if message.get("has_draft") or float(message.get("age_hours", 0)) <= 24:
            continue
        subject = message["subject"]
        found.append(
            {
                "id": f"flagged:{subject}",
                "text": f"Alert: flagged mail has no draft — {subject}.",
            }
        )
    return [item for item in found if item["id"] not in known_ids]


def memory_text(rows: list[dict]) -> str:
    lines = ["# Memory", ""]
    if not rows:
        lines.append("No journal entries yet.")
    for row in rows:
        lines.append(f"- {row.get('timestamp', '')} {row.get('source', '')}: {row.get('event', '')}")
    return "\n".join(lines) + "\n"


def health_text(*, openai_ok: bool, openai_cached: bool, ollama_ok: bool) -> str:
    cloud = "cached success" if openai_cached else ("ok" if openai_ok else "down")
    local = "ok" if ollama_ok else "down"
    return f"Health: OpenAI {cloud}; Ollama {local}."
