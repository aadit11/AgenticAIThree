"""Install the five Lumen jobs into the local Hermes scheduler."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home() / "AppData" / "Local" / "hermes"
SCRIPTS = HOME / "scripts"

JOBS = (
    ("0 8 * * *", "lumen-briefing", "lumen_briefing.py", ["briefing", "--notify"]),
    ("0 21 * * *", "lumen-recap", "lumen_recap.py", ["recap", "--notify"]),
    ("*/30 * * * *", "lumen-alerts", "lumen_alerts.py", ["alerts", "--notify"]),
    ("15 * * * *", "lumen-consolidate", "lumen_consolidate.py", ["consolidate"]),
    ("*/10 * * * *", "lumen-health", "lumen_health.py", ["health"]),
)


def main() -> None:
    SCRIPTS.mkdir(parents=True, exist_ok=True)
    for _, _, filename, args in JOBS:
        script = SCRIPTS / filename
        script.write_text(
            "import sys\n"
            f"sys.path.insert(0, r'{ROOT}')\n"
            "from cron.cli import main\n"
            f"main({args!r})\n",
            encoding="utf-8",
        )
    listed = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True)
    existing = listed.stdout
    for schedule, name, filename, _ in JOBS:
        if name in existing:
            print("exists", name)
            continue
        created = subprocess.run(
            [
                "hermes",
                "cron",
                "create",
                schedule,
                "--name",
                name,
                "--script",
                filename,
                "--no-agent",
                "--workdir",
                str(ROOT),
            ],
            capture_output=True,
            text=True,
        )
        print(name, "create", created.returncode)
        if created.returncode != 0:
            print(created.stdout)
            print(created.stderr)
            raise SystemExit(created.returncode)


if __name__ == "__main__":
    main()
