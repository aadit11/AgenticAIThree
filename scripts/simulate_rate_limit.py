"""Create or remove the local simulation flag. This does not call OpenAI."""

import sys
from pathlib import Path

FLAG = Path(__file__).resolve().parents[1] / "router" / "FORCE_LOCAL"


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "on":
        FLAG.write_text("1\n", encoding="utf-8")
        print("simulation on")
        return
    if command == "off":
        FLAG.unlink(missing_ok=True)
        print("simulation off")
        return
    raise SystemExit("usage: python scripts/simulate_rate_limit.py on|off")


if __name__ == "__main__":
    main()
