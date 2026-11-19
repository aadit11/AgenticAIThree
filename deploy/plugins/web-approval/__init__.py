"""Stop the web chat from waiting on an approval button it cannot show.

Assignment3_local_Gemma.pdf, Part 1 step 8. Telegram, Discord, and Slack keep
their approval path. A request whose platform is api_server is refused instead.
"""

from __future__ import annotations

from typing import Any

_PLATFORM: dict[str, str] = {}

BLOCK_MESSAGE = (
    "This action needs human approval, which the web chat cannot show. "
    "Save a draft instead, or ask me in Telegram/Discord to approve it there."
)


def _on_pre_llm_call(session_id: str = "", platform: str = "", **_kwargs: Any) -> None:
    if session_id:
        _PLATFORM[session_id] = platform or ""


def platform_for(session_id: str) -> str:
    recorded = _PLATFORM.get(session_id or "", "")
    if recorded:
        return recorded
    try:
        from gateway.session_context import get_session_env

        return get_session_env("HERMES_SESSION_PLATFORM", "") or ""
    except Exception:
        return ""


def _command(args: Any) -> str:
    if not isinstance(args, dict):
        return ""
    parts: list[str] = []
    for key in ("command", "cmd", "code", "text"):
        value = args.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def _is_mail_send(command: str) -> bool:
    lowered = command.lower()
    if "email_tool.py" not in lowered:
        return False
    return " send" in f" {lowered}"


def _is_dangerous_shell(tool_name: str, command: str) -> bool:
    if tool_name not in {"terminal", "execute_code", "shell"} or not command.strip():
        return False
    try:
        from tools.approval import detect_dangerous_command
    except Exception:
        return False
    try:
        dangerous, _pattern, _description = detect_dangerous_command(command)
    except Exception:
        return False
    return bool(dangerous)


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    session_id: str = "",
    **_kwargs: Any,
) -> dict[str, str] | None:
    if platform_for(session_id) != "api_server":
        return None
    command = _command(args)
    if _is_mail_send(command) or _is_dangerous_shell(tool_name, command):
        return {"action": "block", "message": BLOCK_MESSAGE}
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
