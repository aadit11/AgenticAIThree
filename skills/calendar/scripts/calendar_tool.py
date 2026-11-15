"""Print today's events, conflicts, and gaps. The iCal URL is never printed."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from lib.calendar_ics import conflicts, events_on, gaps, parse_ics  # noqa: E402
from lib.envfile import load_project_env, require  # noqa: E402


def load_text(args: argparse.Namespace) -> str:
    if args.fixture:
        return Path(args.fixture).read_text(encoding="utf-8")
    load_project_env()
    url = require("CALENDAR_ICS_URL")
    request = Request(url, headers={"User-Agent": "lumen-assignment/0.1"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="")
    parser.add_argument("--day", default="")
    args = parser.parse_args()
    day = datetime.fromisoformat(args.day) if args.day else datetime.now().astimezone()
    events = events_on(parse_ics(load_text(args)), day)
    payload = {
        "day": day.date().isoformat(),
        "events": [
            {"summary": item.summary, "start": item.start.isoformat(), "end": item.end.isoformat()}
            for item in events
        ],
        "conflicts": [[left.summary, right.summary] for left, right in conflicts(events)],
        "gaps": [[start.isoformat(), end.isoformat()] for start, end in gaps(events, day)],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
