"""Search the web and mark every snippet as untrusted data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from lib.search_tool import search  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()
    rows = [
        {"title": item.title, "text": item.text, "url": item.url, "untrusted": item.untrusted}
        for item in search(args.query)
    ]
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
