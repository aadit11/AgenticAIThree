"""The grader chat page is served on the public port and API calls are proxied."""

import importlib.util
import json
import os
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _Backend(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.split("?", 1)[0] != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        reply = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "seen " + payload["messages"][-1]["content"],
                    }
                }
            ]
        }
        body = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def _load_ui(listen: int, backend: int):
    os.environ["PORT"] = str(listen)
    os.environ["HERMES_PORT"] = str(backend)
    spec = importlib.util.spec_from_file_location("lumen_web_ui", ROOT / "deploy" / "web_ui.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebUiTests(unittest.TestCase):
    def test_chat_page_and_proxy(self):
        backend = ThreadingHTTPServer(("127.0.0.1", 0), _Backend)
        backend_port = backend.server_address[1]
        backend_thread = threading.Thread(target=backend.serve_forever, daemon=True)
        backend_thread.start()
        ui = _load_ui(0, backend_port)
        front = ui.ThreadedServer(("127.0.0.1", 0), ui.ProxyHandler)
        front_port = front.server_address[1]
        front_thread = threading.Thread(target=front.serve_forever, daemon=True)
        front_thread.start()
        try:
            page = urllib.request.urlopen(f"http://127.0.0.1:{front_port}/", timeout=5)
            html = page.read().decode("utf-8")
            self.assertIn("Hermes Agent", html)
            self.assertIn("API_SERVER_KEY", html)
            health = urllib.request.urlopen(f"http://127.0.0.1:{front_port}/health", timeout=5)
            self.assertEqual(health.status, 200)
            body = json.dumps(
                {"model": "hermes-agent", "messages": [{"role": "user", "content": "ping"}]}
            ).encode()
            request = urllib.request.Request(
                f"http://127.0.0.1:{front_port}/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer test-key"},
                method="POST",
            )
            reply = json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))
            self.assertEqual(reply["choices"][0]["message"]["content"], "seen ping")
        finally:
            front.shutdown()
            backend.shutdown()


if __name__ == "__main__":
    unittest.main()
