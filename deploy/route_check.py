"""One Gemma call and one cloud call from inside the instance. Prints no secrets."""

from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path("/opt/lumen/app")
sys.path.insert(0, str(ROOT))

from router.execute import cloud_complete, execute, local_complete  # noqa: E402
from router.router import Task  # noqa: E402

LOG = Path("/hermes/phase6-router.log")


def _wait_for_ollama() -> None:
    last = "not-ready"
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
                if response.status == 200:
                    print("isolation: ollama reachable through tailscale", flush=True)
                    return
        except Exception as exc:
            last = type(exc).__name__
        time.sleep(2)
    print(f"isolation: ollama not reachable {last}", flush=True)


def _one(label: str, task: Task) -> None:
    try:
        outcome = execute(
            task,
            "Reply with the single word pong.",
            cloud=cloud_complete,
            local=lambda prompt: local_complete(prompt, timeout=300),
            log_path=LOG,
        )
        print(f"{label} {outcome.reason} {outcome.model_answered} {outcome.success}", flush=True)
    except Exception as exc:
        print(f"{label} failed {type(exc).__name__}", flush=True)


def main() -> None:
    _wait_for_ollama()
    _one("local", Task("summarize", simple=True, local_up=True))
    _one("cloud", Task("brief", simple=False, local_up=True))


if __name__ == "__main__":
    main()
