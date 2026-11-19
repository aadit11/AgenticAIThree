"""Call the model the router chose, then append one log line."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from router.router import CLOUD_MODEL, LOCAL_MODEL, Decision, Task, route

ROOT = Path(__file__).resolve().parents[1]
FLAG_PATH = ROOT / "router" / "FORCE_LOCAL"
LOG_PATH = ROOT / "var" / "router.log"
LA = ZoneInfo("America/Los_Angeles")


class CloudHTTPError(Exception):
    def __init__(self, status: int):
        super().__init__(f"cloud status {status}")
        self.status = status


@dataclass(frozen=True)
class Outcome:
    timestamp: str
    task_type: str
    reason: str
    model_requested: str
    model_answered: str
    success: bool
    latency_ms: int
    text: str


def simulation_on(env: dict[str, str] | None = None, flag_path: Path = FLAG_PATH) -> bool:
    values = os.environ if env is None else env
    if values.get("SIMULATE_RATE_LIMIT") == "1":
        return True
    return flag_path.is_file()


def apply_simulation(task: Task, env: dict[str, str] | None = None, flag_path: Path = FLAG_PATH) -> Task:
    if task.simulate_rate_limit or simulation_on(env, flag_path):
        return Task(
            task.kind,
            privacy=task.privacy,
            simple=task.simple,
            fits_local_context=task.fits_local_context,
            local_up=task.local_up,
            simulate_rate_limit=True,
            cloud_status=task.cloud_status,
        )
    return task


def route_target(reason: str, model: str) -> str:
    """local, cloud, or held. The log never includes the message text."""
    if reason == "held":
        return "held"
    if reason in {
        "simple",
        "privacy",
        "simulated_rate_limit",
        "cloud_rate_limit",
        "cloud_model_unavailable",
    } or model.startswith("gemma"):
        return "local"
    return "cloud"


def log_line(outcome: Outcome) -> str:
    return json.dumps(
        {
            "component": "lumen-router",
            "timestamp": outcome.timestamp,
            "task_type": outcome.task_type,
            "reason": outcome.reason,
            "target": route_target(outcome.reason, outcome.model_answered or outcome.model_requested),
            "model_requested": outcome.model_requested,
            "model_answered": outcome.model_answered,
            "success": outcome.success,
            "latency_ms": outcome.latency_ms,
        },
        separators=(",", ":"),
    )


def append_log(outcome: Outcome, log_path: Path = LOG_PATH) -> None:
    line = log_line(outcome)
    print(line)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def execute(
    task: Task,
    prompt: str,
    *,
    cloud,
    local,
    log_path: Path = LOG_PATH,
    flag_path: Path = FLAG_PATH,
    env: dict[str, str] | None = None,
) -> Outcome:
    """Route, call only the chosen backend, and log the result."""
    chosen = route(apply_simulation(task, env, flag_path))
    started = time.perf_counter()
    text = ""
    answered = ""
    success = False
    reason = chosen.reason
    requested = chosen.model
    try:
        text, answered, reason, requested = _call(chosen, task, prompt, cloud, local)
        success = True
    except Exception:
        success = False
        raise
    finally:
        elapsed = int((time.perf_counter() - started) * 1000)
        outcome = Outcome(
            datetime.now(LA).isoformat(timespec="seconds"),
            task.kind,
            reason,
            requested,
            answered,
            success,
            elapsed,
            text,
        )
        append_log(outcome, log_path)
    return outcome


def _call(chosen: Decision, task: Task, prompt: str, cloud, local) -> tuple[str, str, str, str]:
    if not chosen.call_cloud:
        text, answered = local(prompt)
        return text, answered, chosen.reason, chosen.model
    try:
        text, answered = cloud(prompt)
        return text, answered, chosen.reason, chosen.model
    except CloudHTTPError as error:
        if error.status == 429 and task.local_up:
            text, answered = local(prompt)
            return text, answered, "cloud_rate_limit", LOCAL_MODEL
        if error.status == 404 and task.local_up:
            text, answered = local(prompt)
            return text, answered, "cloud_model_unavailable", LOCAL_MODEL
        raise


def cloud_complete(prompt: str, timeout: int = 120) -> tuple[str, str]:
    """One OpenAI chat completion. Uses max_completion_tokens."""
    from lib.envfile import require

    body = json.dumps(
        {
            "model": CLOUD_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 32,
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + require("OPENAI_API_KEY"),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise CloudHTTPError(error.code) from None
    message = payload["choices"][0]["message"].get("content") or ""
    return message.strip(), payload.get("model") or CLOUD_MODEL


def local_complete(prompt: str, timeout: int = 180) -> tuple[str, str]:
    """One Ollama chat. Thinking is off and the model stays loaded."""
    from lib.envfile import load_project_env

    load_project_env()
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", LOCAL_MODEL)
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {"num_predict": 32},
        }
    ).encode()
    request = urllib.request.Request(
        base + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    message = (payload.get("message") or {}).get("content") or ""
    return message.strip(), payload.get("model") or model


def live() -> None:
    """One local call and one cloud call, then a simulated short task."""
    local_task = Task("summarize", simple=True, local_up=True)
    cloud_task = Task("brief", simple=False, local_up=True)
    local_outcome = execute(local_task, "Reply with the single word pong.", cloud=cloud_complete, local=local_complete)
    cloud_outcome = execute(cloud_task, "Reply with the single word pong.", cloud=cloud_complete, local=local_complete)
    FLAG_PATH.write_text("1\n", encoding="utf-8")
    try:
        simulated = execute(
            Task("summarize", simple=True, local_up=True),
            "Reply with the single word pong.",
            cloud=_cloud_must_not_run,
            local=local_complete,
        )
    finally:
        FLAG_PATH.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "local_reason": local_outcome.reason,
                "local_model": local_outcome.model_answered,
                "cloud_reason": cloud_outcome.reason,
                "cloud_model": cloud_outcome.model_answered,
                "simulated_reason": simulated.reason,
                "simulated_model": simulated.model_answered,
            }
        )
    )


def _cloud_must_not_run(prompt: str) -> tuple[str, str]:
    raise AssertionError("OpenAI was contacted during simulation")


if __name__ == "__main__":
    live()
