"""Turn a chat message into the task the router already understands."""

from __future__ import annotations

from router.router import Task

SIMPLE_MARKERS = (
    "one line",
    "one-line",
    "in one sentence",
    "urgent or not",
    "urgent/not",
)
PRIVACY_MARKERS = ("marked private", "keep this private", "private note")


def message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def last_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message_text(message.get("content"))
    return ""


def has_tool_result(messages: list[dict]) -> bool:
    for message in messages:
        if message.get("role") == "tool":
            return True
        if message.get("role") == "assistant" and message.get("tool_calls"):
            return True
    return False


def classify_turn(text: str, *, has_tool_followup: bool) -> Task:
    """Short or private text stays local. Tool follow-ups stay on the cloud model."""
    lowered = text.lower()
    privacy = any(marker in lowered for marker in PRIVACY_MARKERS)
    simple = (
        any(marker in lowered for marker in SIMPLE_MARKERS)
        or lowered.startswith("summarize:")
        or lowered.startswith("summary:")
    )
    if has_tool_followup:
        privacy = False
        simple = False
    if privacy:
        kind = "rewrite"
    elif simple:
        kind = "summarize"
    else:
        kind = "brief"
    return Task(
        kind,
        privacy=privacy,
        simple=simple and not privacy,
        fits_local_context=len(text) < 8000,
        local_up=True,
    )


def cloud_payload(body: dict) -> dict:
    """Forward a Hermes completion to gpt-6.1-sol. That model rejects max_tokens."""
    payload: dict = {
        "model": "gpt-6.1-sol",
        "messages": body.get("messages") or [],
    }
    if body.get("tools"):
        payload["tools"] = body["tools"]
    if body.get("tool_choice") not in (None, "none"):
        payload["tool_choice"] = body["tool_choice"]
    limit = body.get("max_completion_tokens") or body.get("max_tokens")
    if limit:
        payload["max_completion_tokens"] = limit
    return payload
