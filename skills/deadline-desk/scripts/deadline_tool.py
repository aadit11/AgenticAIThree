"""Report deadline urgency and one study block."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from lib.calendar_ics import parse_ics  # noqa: E402
from lib.deadlines import load_deadlines, suggest_block, urgency  # noqa: E402
from lib.envfile import load_project_env, require  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", default="")
    parser.add_argument("--deadlines", default=str(ROOT / "synthetic" / "deadlines.json"))
    parser.add_argument("--calendar", default=str(ROOT / "synthetic" / "fixtures" / "calendar.ics"))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now().astimezone()
    if args.live:
        load_project_env()
        request = Request(require("CALENDAR_ICS_URL"), headers={"User-Agent": "lumen-assignment/0.1"})
        with urlopen(request, timeout=20) as response:
            calendar_text = response.read().decode("utf-8", errors="replace")
    else:
        calendar_text = Path(args.calendar).read_text(encoding="utf-8")
    events = parse_ics(calendar_text)
    rows = []
    for item in load_deadlines(Path(args.deadlines)):
        block = None if item.status == "submitted" or item.due <= now else suggest_block(events, item, now)
        rows.append(
            {
                "title": item.title,
                "course": item.course,
                "due": item.due.isoformat(),
                "urgency": urgency(item, now),
                "study_block": [block[0].isoformat(), block[1].isoformat()] if block else None,
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
