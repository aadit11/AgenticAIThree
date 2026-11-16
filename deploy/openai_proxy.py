"""OpenAI-compatible proxy. Hermes talks to this process for every chat turn."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(os.environ.get("LUMEN_APP", "/opt/lumen/app"))
sys.path.insert(0, str(APP))

from router.bridge import chat_from_responses, responses_request_from_chat  # noqa: E402
from router.classify import classify_turn, cloud_payload, has_tool_result, last_user_text  # noqa: E402
from router.execute import (  # noqa: E402
    CloudHTTPError,
    append_log,
    apply_simulation,
    local_complete,
)
from router.router import route  # noqa: E402

LISTEN = os.environ.get("LUMEN_ROUTER_LISTEN", "127.0.0.1:8642")
HOME = Path(os.environ.get("HERMES_HOME", "/tmp"))
LOG_PATH = HOME / "var" / "router.log"
FLAG_PATH = HOME / "FORCE_LOCAL"


def local_up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print(f"isolation: ollama tags failed {type(error).__name__}", flush=True)
        return False
    names = [item.get("name", "") for item in payload.get("models") or []]
    return any(name.startswith("gemma4") for name in names)


def openai_request(payload: dict, url: str = "https://api.openai.com/v1/chat/completions") -> tuple[int, bytes, str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise CloudHTTPError(401)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "application/json")
            return response.status, response.read(), content_type
    except urllib.error.HTTPError as error:
        raise CloudHTTPError(error.code) from None


def local_response(prompt: str) -> tuple[str, str]:
    text, model = local_complete(prompt, timeout=180)
    body = {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
    }
    return text, json.dumps(body)


def completion(body: dict) -> tuple[int, bytes, str]:
    """Return HTTP status, body, and content type."""
    messages = body.get("messages") or []
    user_text = last_user_text(messages) or " "
    task = classify_turn(user_text, has_tool_followup=has_tool_result(messages))
    task = apply_simulation(
        task.__class__(
            task.kind,
            privacy=task.privacy,
            simple=task.simple,
            fits_local_context=task.fits_local_context,
            local_up=local_up(),
            simulate_rate_limit=task.simulate_rate_limit,
            cloud_status=task.cloud_status,
        ),
        flag_path=FLAG_PATH,
    )
    chosen = route(task)
    stream = bool(body.get("stream"))
    started = time.perf_counter()

    def finish_local(reason: str, requested: str) -> tuple[int, bytes, str]:
        _text, raw = local_response(user_text)
        _log(task.kind, reason, requested, json.loads(raw)["model"], True, started)
        if stream:
            return 200, as_sse(raw), "text/event-stream"
        return 200, raw.encode(), "application/json"

    if not chosen.call_cloud:
        try:
            return finish_local(chosen.reason, chosen.model)
        except Exception:
            _log(task.kind, chosen.reason, chosen.model, "", False, started)
            raise
    try:
        if body.get("tools"):
            _status, raw_body, content_type = openai_request(
                responses_request_from_chat(body),
                "https://api.openai.com/v1/responses",
            )
            parsed = json.loads(raw_body.decode("utf-8"))
            if parsed.get("status") == "failed":
                raise CloudHTTPError(502)
            content_type = "application/json"
            raw_body = json.dumps(chat_from_responses(parsed)).encode()
        else:
            _status, raw_body, content_type = openai_request(cloud_payload(body))
    except CloudHTTPError as error:
        if error.status in {404, 429} and task.local_up:
            reason = "cloud_model_unavailable" if error.status == 404 else "cloud_rate_limit"
            return finish_local(reason, "gemma4:e2b")
        _log(task.kind, chosen.reason, chosen.model, "", False, started)
        raise
    if "event-stream" in content_type:
        _log(task.kind, chosen.reason, chosen.model, chosen.model, True, started)
        return 200, raw_body, "text/event-stream"
    payload = json.loads(raw_body.decode("utf-8"))
    answered = payload.get("model") or chosen.model
    _log(task.kind, chosen.reason, chosen.model, answered, True, started)
    if stream:
        return 200, as_sse(json.dumps(payload)), "text/event-stream"
    return 200, json.dumps(payload).encode(), "application/json"


def _log(kind: str, reason: str, requested: str, answered: str, success: bool, started: float) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from router.execute import Outcome

    append_log(
        Outcome(
            datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
            kind,
            reason,
            requested,
            answered,
            success,
            int((time.perf_counter() - started) * 1000),
            "",
        ),
        LOG_PATH,
    )


def as_sse(raw: str) -> bytes:
    payload = json.loads(raw)
    message = (payload.get("choices") or [{}])[0].get("message") or {}
    content = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []
    header = {
        "id": payload.get("id", "chatcmpl-local"),
        "object": "chat.completion.chunk",
        "model": payload.get("model", ""),
    }
    pieces: list[str] = []

    def emit(delta: dict, finish: str | None) -> None:
        chunk = dict(header)
        chunk["choices"] = [{"index": 0, "delta": delta, "finish_reason": finish}]
        pieces.append("data: " + json.dumps(chunk) + "\n\n")

    if tool_calls:
        for index, call in enumerate(tool_calls):
            function = call.get("function") or {}
            delta = {
                "tool_calls": [
                    {
                        "index": index,
                        "id": call.get("id"),
                        "type": call.get("type") or "function",
                        "function": {
                            "name": function.get("name") or "",
                            "arguments": function.get("arguments") or "",
                        },
                    }
                ]
            }
            if index == 0:
                delta["role"] = "assistant"
                if content:
                    delta["content"] = content
            emit(delta, None)
    else:
        emit({"role": "assistant", "content": content}, None)
    emit({}, "tool_calls" if tool_calls else "stop")
    pieces.append("data: [DONE]\n\n")
    return "".join(pieces).encode()


def responses_completion(body: dict) -> tuple[int, bytes, str]:
    """Forward a Responses API call. gpt-6.1-sol stays on that API when Hermes asks for it."""
    raw_input = body.get("input")
    if isinstance(raw_input, str):
        user_text = raw_input
        tool_followup = False
    elif isinstance(raw_input, list):
        user_text = last_user_text(raw_input)
        tool_followup = has_tool_result(raw_input) or any(
            isinstance(item, dict) and item.get("type") in {"function_call", "function_call_output"}
            for item in raw_input
        )
    else:
        user_text = ""
        tool_followup = False
    task = classify_turn(user_text or " ", has_tool_followup=tool_followup)
    task = apply_simulation(
        task.__class__(
            task.kind,
            privacy=task.privacy,
            simple=task.simple,
            fits_local_context=task.fits_local_context,
            local_up=local_up(),
            simulate_rate_limit=task.simulate_rate_limit,
            cloud_status=task.cloud_status,
        ),
        flag_path=FLAG_PATH,
    )
    chosen = route(task)
    started = time.perf_counter()
    want_stream = bool(body.get("stream"))
    payload = dict(body)
    payload["model"] = "gpt-6.1-sol"
    payload.pop("stream", None)
    if not chosen.call_cloud:
        text, model = local_complete(user_text or " ", timeout=180)
        _log(task.kind, chosen.reason, chosen.model, model, True, started)
        raw = json.dumps(
            {
                "id": "resp-local",
                "object": "response",
                "status": "completed",
                "model": model,
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": text}],
                    }
                ],
            }
        ).encode()
        if want_stream:
            return 200, responses_sse(raw), "text/event-stream"
        return 200, raw, "application/json"
    try:
        _status, raw_body, content_type = openai_request(payload, "https://api.openai.com/v1/responses")
    except CloudHTTPError as error:
        if error.status in {404, 429} and task.local_up:
            text, model = local_complete(user_text or " ", timeout=180)
            reason = "cloud_model_unavailable" if error.status == 404 else "cloud_rate_limit"
            _log(task.kind, reason, "gemma4:e2b", model, True, started)
            raw = json.dumps({"id": "resp-local", "object": "response", "status": "completed", "model": model, "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}]}).encode()
            if want_stream:
                return 200, responses_sse(raw), "text/event-stream"
            return 200, raw, "application/json"
        _log(task.kind, chosen.reason, chosen.model, "", False, started)
        raise
    _log(task.kind, chosen.reason, chosen.model, chosen.model, True, started)
    if want_stream:
        return 200, responses_sse(raw_body), "text/event-stream"
    return 200, raw_body, content_type.split(";")[0] or "application/json"


def responses_sse(raw: bytes) -> bytes:
    """One completed Responses event. Hermes stops the stream on response.completed."""
    payload = json.loads(raw.decode("utf-8"))
    texts = []
    for item in payload.get("output") or []:
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("text"):
                texts.append(part["text"])
    delta = {"type": "response.output_text.delta", "delta": "".join(texts)}
    completed = {"type": "response.completed", "response": payload}
    return (
        "event: response.output_text.delta\ndata: "
        + json.dumps(delta)
        + "\n\nevent: response.completed\ndata: "
        + json.dumps(completed)
        + "\n\ndata: [DONE]\n\n"
    ).encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0].rstrip("/").endswith("/models"):
            body = json.dumps(
                {"object": "list", "data": [{"id": "gpt-6.1-sol", "object": "model"}]}
            ).encode()
            self._send(200, body, "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        if not path.endswith("/chat/completions") and not path.endswith("/responses"):
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 8_000_000:
            self._send(413, b"too large", "text/plain")
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if path.endswith("/responses"):
                status, payload, content_type = responses_completion(body)
            else:
                status, payload, content_type = completion(body)
        except CloudHTTPError as error:
            print(f"isolation: router upstream {error.status}", flush=True)
            self._send(502, b'{"error":{"message":"router failed"}}', "application/json")
            return
        except Exception as error:
            print(f"isolation: router proxy failed {type(error).__name__}", flush=True)
            self._send(502, b'{"error":{"message":"router failed"}}', "application/json")
            return
        self._send(status, payload, content_type)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host, _, port = LISTEN.partition(":")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    print("isolation: router proxy up", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
