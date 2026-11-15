"""Run one Lumen job. Printing is the message. Email is never sent."""

from __future__ import annotations

import imaplib
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cron.journal import append, read  # noqa: E402
from cron.logic import (  # noqa: E402
    briefing_text,
    health_text,
    memory_text,
    new_alerts,
    open_deadlines,
    recap_text,
)
from lib.calendar_ics import events_on, gaps, parse_ics  # noqa: E402
from lib.deadlines import load_deadlines  # noqa: E402
from lib.envfile import load_project_env, require  # noqa: E402

LA = ZoneInfo("America/Los_Angeles")
JOURNAL = ROOT / "var" / "journal.jsonl"
ALERTS = ROOT / "var" / "alert_ids.json"
DRAFTS = ROOT / "var" / "drafts.json"
MEMORY = ROOT / "hermes" / "MEMORY.md"
HEALTH_CACHE = ROOT / "var" / "health_cache.json"
DEADLINES = ROOT / "synthetic" / "deadlines.json"
PROTECTED = (ROOT / "hermes" / "USER.md", ROOT / "hermes" / "SOUL.md")


def _now() -> datetime:
    return datetime.now(LA)


def _calendar_text() -> str:
    load_project_env()
    request = urllib.request.Request(require("CALENDAR_ICS_URL"), headers={"User-Agent": "lumen-assignment/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _forecast() -> str:
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=34.0522&longitude=-118.2437"
        "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min"
        "&temperature_unit=fahrenheit&timezone=America%2FLos_Angeles&forecast_days=1"
    )
    last_error: Exception | None = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                payload = json.loads(response.read().decode("utf-8"))
            last_error = None
            break
        except Exception as error:
            last_error = error
    if last_error is not None:
        return _forecast_fallback()
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    temp = current.get("temperature_2m")
    high = (daily.get("temperature_2m_max") or [None])[0]
    low = (daily.get("temperature_2m_min") or [None])[0]
    return f"Los Angeles {temp}F now, high {high}F, low {low}F"


def _forecast_fallback() -> str:
    """Open-Meteo is preferred. weather.gov is used only when that request fails."""
    headers = {"User-Agent": "lumen-assignment/0.1 (class project)", "Accept": "application/geo+json"}
    point = urllib.request.Request("https://api.weather.gov/points/34.0522,-118.2437", headers=headers)
    with urllib.request.urlopen(point, timeout=30) as response:
        forecast_url = json.loads(response.read().decode("utf-8"))["properties"]["forecast"]
    forecast = urllib.request.Request(forecast_url, headers=headers)
    with urllib.request.urlopen(forecast, timeout=30) as response:
        period = json.loads(response.read().decode("utf-8"))["properties"]["periods"][0]
    return f"Los Angeles {period['temperature']}F, {period['shortForecast']} ({period['name']})"


def _mailbox():
    load_project_env()
    box = imaplib.IMAP4_SSL(require("EMAIL_IMAP_HOST"), int(require("EMAIL_IMAP_PORT")))
    box.login(require("EMAIL_ADDRESS"), require("EMAIL_APP_PASSWORD").replace(" ", ""))
    box.select("INBOX")
    return box


def _subjects(box, criteria: str) -> list[str]:
    status, data = box.search(None, criteria)
    if status != "OK" or not data or not data[0]:
        return []
    subjects = []
    for number in data[0].split()[-8:]:
        fetched, msg = box.fetch(number, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
        if fetched != "OK" or not msg or not isinstance(msg[0], tuple):
            continue
        header = message_from_bytes(msg[0][1])
        subjects.append(header.get("Subject", "(no subject)"))
    return subjects


def _flagged(box, now: datetime) -> list[dict]:
    status, data = box.search(None, "FLAGGED")
    if status != "OK" or not data or not data[0]:
        return []
    drafts = _pending_drafts()
    rows = []
    for number in data[0].split():
        fetched, msg = box.fetch(number, "(INTERNALDATE BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
        if fetched != "OK" or not msg:
            continue
        meta = msg[0][0].decode("utf-8", "replace") if isinstance(msg[0], tuple) else ""
        header = message_from_bytes(msg[0][1]) if isinstance(msg[0], tuple) else message_from_bytes(b"")
        subject = header.get("Subject", "(no subject)")
        age_hours = 0.0
        marker = 'INTERNALDATE "'
        if marker in meta:
            raw = meta.split(marker, 1)[1].split('"', 1)[0]
            when = parsedate_to_datetime(raw)
            age_hours = (now - when.astimezone(LA)).total_seconds() / 3600
        rows.append(
            {
                "subject": subject,
                "age_hours": age_hours,
                "has_draft": any(subject in item for item in drafts),
            }
        )
    return rows


def _pending_drafts() -> list[str]:
    if not DRAFTS.is_file():
        return []
    rows = json.loads(DRAFTS.read_text(encoding="utf-8"))
    pending = []
    for draft_id, item in rows.items():
        if not item.get("sent"):
            pending.append(draft_id)
    return pending


def _known_alerts() -> set[str]:
    if not ALERTS.is_file():
        return set()
    return set(json.loads(ALERTS.read_text(encoding="utf-8")))


def _save_alerts(ids: set[str]) -> None:
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    ALERTS.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")


def _notify(text: str) -> None:
    load_project_env()
    body = json.dumps({"chat_id": require("TELEGRAM_ALLOWED_USER_ID"), "text": text}).encode()
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + require("TELEGRAM_BOT_TOKEN") + "/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError("telegram send failed")


def run_briefing(notify: bool = False) -> str:
    now = _now()
    events = events_on(parse_ics(_calendar_text()), now)
    event_lines = [f"{item.summary} {item.start.strftime('%H:%M')}-{item.end.strftime('%H:%M')}" for item in events]
    gap_lines = [f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}" for start, end in gaps(events, now)]
    box = _mailbox()
    try:
        mail_lines = [f"unread: {subject}" for subject in _subjects(box, "UNSEEN")]
        mail_lines += [f"flagged: {subject}" for subject in _subjects(box, "FLAGGED")]
    finally:
        box.logout()
    due = open_deadlines(load_deadlines(DEADLINES), now, 7)
    text = briefing_text(
        day=now.date().isoformat(),
        events=event_lines,
        gaps=gap_lines,
        forecast=_forecast(),
        mail_lines=mail_lines,
        deadline_lines=[f"{item.title} due {item.due.strftime('%b %d')}" for item in due],
    )
    if notify:
        _notify(text)
    append(JOURNAL, "briefing", "morning briefing")
    return text


def run_recap(notify: bool = False) -> str:
    now = _now()
    tomorrow = now + timedelta(days=1)
    events = events_on(parse_ics(_calendar_text()), tomorrow)
    text = recap_text(
        day=now.date().isoformat(),
        journal_lines=[f"{row['source']}: {row['event']}" for row in read(JOURNAL) if row["timestamp"].startswith(now.date().isoformat())],
        pending_drafts=_pending_drafts(),
        tomorrow_events=[f"{item.summary} {item.start.strftime('%H:%M')}" for item in events],
    )
    if notify:
        _notify(text)
    append(JOURNAL, "recap", "end of day")
    return text


def run_alerts(notify: bool = False) -> str:
    now = _now()
    events = events_on(parse_ics(_calendar_text()), now)
    box = _mailbox()
    try:
        flagged = _flagged(box, now)
    finally:
        box.logout()
    fresh = new_alerts(
        now=now,
        events=[(item.summary, item.start) for item in events],
        deadlines=load_deadlines(DEADLINES),
        flagged=flagged,
        known_ids=_known_alerts(),
    )
    lines = [item["text"] for item in fresh]
    if notify:
        for line in lines:
            _notify(line)
    if fresh:
        known = _known_alerts()
        known.update(item["id"] for item in fresh)
        _save_alerts(known)
    append(JOURNAL, "alert", f"{len(fresh)} new")
    return "\n".join(lines)


def run_consolidate() -> str:
    before = {path: path.read_bytes() for path in PROTECTED if path.is_file()}
    text = memory_text(read(JOURNAL))
    MEMORY.parent.mkdir(parents=True, exist_ok=True)
    MEMORY.write_text(text, encoding="utf-8")
    home_memory = Path.home() / "AppData" / "Local" / "hermes" / "MEMORY.md"
    if home_memory.parent.is_dir():
        home_memory.write_text(text, encoding="utf-8")
    for path, payload in before.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"consolidator rewrote {path.name}")
    append(JOURNAL, "consolidate", f"{len(read(JOURNAL))} journal rows folded")
    return f"Memory updated ({MEMORY.name})."


def run_health() -> str:
    cached = False
    openai_ok = False
    cache = {}
    if HEALTH_CACHE.is_file():
        cache = json.loads(HEALTH_CACHE.read_text(encoding="utf-8"))
    last = cache.get("openai_at", "")
    if last:
        previous = datetime.fromisoformat(last)
        cached = _now() - previous < timedelta(hours=6) and cache.get("openai_ok") is True
    if cached:
        openai_ok = True
    else:
        openai_ok = _ping_openai()
        HEALTH_CACHE.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_CACHE.write_text(
            json.dumps({"openai_at": _now().isoformat(timespec="seconds"), "openai_ok": openai_ok}),
            encoding="utf-8",
        )
    ollama_ok = _ping_ollama()
    text = health_text(openai_ok=openai_ok, openai_cached=cached, ollama_ok=ollama_ok)
    append(JOURNAL, "health", text)
    return text


def _ping_openai() -> bool:
    from router.execute import cloud_complete

    text, model = cloud_complete("Reply with the single word ok.", timeout=60)
    return bool(text) and model.startswith("gpt-")


def _ping_ollama() -> bool:
    load_project_env()
    import os

    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    with urllib.request.urlopen(base + "/api/tags", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    names = [item.get("name", "") for item in payload.get("models") or []]
    return any(name.startswith("gemma4") for name in names)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    notify = "--notify" in args
    command = next(item for item in args if not item.startswith("--"))
    runners = {
        "briefing": run_briefing,
        "recap": run_recap,
        "alerts": run_alerts,
        "consolidate": run_consolidate,
        "health": run_health,
    }
    runner = runners[command]
    if command in {"briefing", "recap", "alerts"}:
        text = runner(notify=notify)
    else:
        text = runner()
    if text:
        print(text)


if __name__ == "__main__":
    main()
