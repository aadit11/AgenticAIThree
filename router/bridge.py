"""Translate a chat-completions tool turn into the Responses API and back.

gpt-6.1-sol rejects function tools on /v1/chat/completions. Hermes still speaks
chat completions, so a tool-using turn is rewritten here.
"""

from __future__ import annotations

import json

from router.classify import message_text


def chat_tools_to_responses(tools: list) -> list[dict]:
    converted: list[dict] = []
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            continue
        function = tool.get("function") if isinstance(tool.get("function"), dict) else tool
        name = function.get("name")
        if not name:
            continue
        item = {
            "type": "function",
            "name": name,
            "parameters": function.get("parameters") or {"type": "object", "properties": {}},
        }
        if function.get("description"):
            item["description"] = function["description"]
        converted.append(item)
    return converted


def messages_to_input(messages: list) -> list[dict]:
    items: list[dict] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": str(message.get("tool_call_id") or ""),
                    "output": message_text(message.get("content")) or " ",
                }
            )
            continue
        if role == "assistant" and message.get("tool_calls"):
            content = message_text(message.get("content"))
            if content:
                items.append({"role": "assistant", "content": content})
            for call in message.get("tool_calls") or []:
                if not isinstance(call, dict):
                    continue
                function = call.get("function") if isinstance(call.get("function"), dict) else {}
                arguments = function.get("arguments") or "{}"
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                items.append(
                    {
                        "type": "function_call",
                        "call_id": str(call.get("id") or function.get("name") or "call"),
                        "name": function.get("name") or "",
                        "arguments": arguments,
                    }
                )
            continue
        if role in {"system", "developer", "user", "assistant"}:
            content = message_text(message.get("content"))
            if content:
                items.append({"role": role, "content": content})
    if not items:
        items.append({"role": "user", "content": " "})
    return items


def map_tool_choice(choice: object) -> object | None:
    if choice in (None, "auto", "none", "required"):
        return None if choice is None else choice
    if isinstance(choice, dict):
        function = choice.get("function") if isinstance(choice.get("function"), dict) else {}
        name = function.get("name") or choice.get("name")
        if name:
            return {"type": "function", "name": name}
    return None


def responses_request_from_chat(body: dict) -> dict:
    payload: dict = {
        "model": "gpt-6.1-sol",
        "input": messages_to_input(body.get("messages") or []),
        "tools": chat_tools_to_responses(body.get("tools") or []),
    }
    choice = map_tool_choice(body.get("tool_choice"))
    if choice is not None:
        payload["tool_choice"] = choice
    limit = body.get("max_completion_tokens") or body.get("max_tokens")
    if limit:
        payload["max_output_tokens"] = limit
    return payload


def chat_from_responses(payload: dict) -> dict:
    texts: list[str] = []
    tool_calls: list[dict] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("text"):
                    texts.append(str(part["text"]))
        elif item.get("type") == "function_call":
            arguments = item.get("arguments") or "{}"
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments)
            tool_calls.append(
                {
                    "id": str(item.get("call_id") or item.get("id") or "call"),
                    "type": "function",
                    "function": {"name": item.get("name") or "", "arguments": arguments},
                }
            )
    message: dict = {"role": "assistant", "content": "".join(texts) if texts else None}
    finish = "stop"
    if tool_calls:
        message["tool_calls"] = tool_calls
        finish = "tool_calls"
    return {
        "id": payload.get("id") or "chatcmpl-responses",
        "object": "chat.completion",
        "model": payload.get("model") or "gpt-6.1-sol",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
    }
