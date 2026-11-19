"""Turn on the web-chat approval plugin without dropping the rest of config.yaml."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

NAME = "web-approval"


def main() -> None:
    path = Path(os.environ.get("HERMES_HOME", "/hermes")) / "config.yaml"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if NAME in text:
        print("isolation: web-approval already listed", flush=True)
        return
    try:
        loaded = yaml.safe_load(text) if text.strip() else {}
    except Exception:
        loaded = None
    if not isinstance(loaded, dict):
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\nplugins:\n  enabled:\n    - web-approval\n")
        print("isolation: web-approval appended", flush=True)
        return
    plugins = loaded.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
    enabled = plugins.get("enabled")
    if not isinstance(enabled, list):
        enabled = []
    enabled.append(NAME)
    plugins["enabled"] = enabled
    loaded["plugins"] = plugins
    path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")
    print("isolation: web-approval enabled", flush=True)


if __name__ == "__main__":
    main()
