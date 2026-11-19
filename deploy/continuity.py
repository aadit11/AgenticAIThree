"""Save one synthetic fact, then ask two fresh sessions to recall it."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", "/hermes"))
FACT = "Maya's fictional project codename is Paper Lantern."
MARKER = HOME / "var" / "continuity-done"
MEMORY = HOME / "MEMORY.md"


def _api_base() -> str:
    return "http://127.0.0.1:" + os.environ.get("HERMES_PORT", "8081")


def wait_for_gateway() -> bool:
    for _ in range(60):
        try:
            with urllib.request.urlopen(_api_base() + "/health", timeout=5) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(3)
    return False


def ask(prompt: str) -> str:
    key = os.environ.get("API_SERVER_KEY", "").strip()
    body = json.dumps(
        {"model": "hermes-agent", "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    request = urllib.request.Request(
        _api_base() + "/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


def ensure_fact() -> str:
    existing = MEMORY.read_text(encoding="utf-8") if MEMORY.is_file() else ""
    if FACT in existing:
        return "already stored"
    MEMORY.parent.mkdir(parents=True, exist_ok=True)
    if existing.strip():
        MEMORY.write_text(existing.rstrip() + "\n§\n" + FACT + "\n", encoding="utf-8")
    else:
        MEMORY.write_text(FACT + "\n", encoding="utf-8")
    return "appended"


def main() -> None:
    if MARKER.is_file():
        print("isolation: continuity already checked", flush=True)
        return
    if not wait_for_gateway():
        print("isolation: continuity gateway down", flush=True)
        return
    save_reply = ask(
        "Save this in memory as its own entry, exactly: "
        + FACT
        + " Reply with the single word saved."
    )
    time.sleep(2)
    stored = ensure_fact()
    discord_reply = ask("What is Maya's fictional project codename? Reply with the codename only.")
    slack_reply = ask("What is Maya's fictional project codename? Reply with the codename only.")
    log = HOME / "continuity.log"
    log.write_text(
        "\n".join(
            [
                "save: " + save_reply.replace("\n", " ")[:400],
                "store: " + stored,
                "discord session: " + discord_reply.replace("\n", " ")[:400],
                "slack session: " + slack_reply.replace("\n", " ")[:400],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("done\n", encoding="utf-8")
    recalled = "Paper Lantern" in discord_reply and "Paper Lantern" in slack_reply
    print("isolation: continuity recalled" if recalled else "isolation: continuity stored", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"isolation: continuity failed {type(error).__name__}", flush=True)
