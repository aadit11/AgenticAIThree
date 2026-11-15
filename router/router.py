"""Task-aware choice between gpt-6.1-sol and local Gemma 4."""

from __future__ import annotations

from dataclasses import dataclass


CLOUD_MODEL = "gpt-6.1-sol"
LOCAL_MODEL = "gemma4:e2b"


@dataclass(frozen=True)
class Task:
    kind: str
    privacy: bool = False
    simple: bool = False
    fits_local_context: bool = True
    local_up: bool = True
    simulate_rate_limit: bool = False
    cloud_status: int | None = None


@dataclass(frozen=True)
class Decision:
    model: str
    reason: str
    call_cloud: bool


def route(task: Task) -> Decision:
    """Return the model and the logged reason. A simulation never calls OpenAI."""
    if task.simulate_rate_limit:
        return Decision(LOCAL_MODEL, "simulated_rate_limit", False)
    if task.cloud_status == 429 and task.local_up:
        return Decision(LOCAL_MODEL, "cloud_rate_limit", False)
    if task.cloud_status == 404 and task.local_up:
        return Decision(LOCAL_MODEL, "cloud_model_unavailable", False)
    wants_local = task.simple or (task.privacy and task.fits_local_context)
    if wants_local and task.local_up:
        reason = "privacy" if task.privacy and task.fits_local_context else "simple"
        return Decision(LOCAL_MODEL, reason, False)
    if wants_local and not task.local_up:
        return Decision(CLOUD_MODEL, "local_unavailable", True)
    return Decision(CLOUD_MODEL, "reasoning", True)
