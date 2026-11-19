"""Web-chat sessions cannot wait on an approval button."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _plugin():
    spec = importlib.util.spec_from_file_location(
        "lumen_web_approval",
        ROOT / "deploy" / "plugins" / "web-approval" / "__init__.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebApprovalTests(unittest.TestCase):
    def test_api_server_send_is_blocked_and_chat_send_is_not(self):
        plugin = _plugin()
        plugin._on_pre_llm_call(session_id="web", platform="api_server")
        plugin._on_pre_llm_call(session_id="phone", platform="telegram")
        command = {"command": "python skills/email/scripts/email_tool.py send --draft-id d1"}
        blocked = plugin._on_pre_tool_call("terminal", command, session_id="web")
        self.assertEqual(blocked["action"], "block")
        self.assertIn("web chat", blocked["message"])
        self.assertIsNone(plugin._on_pre_tool_call("terminal", command, session_id="phone"))

    def test_api_server_can_still_read_mail(self):
        plugin = _plugin()
        plugin._on_pre_llm_call(session_id="web", platform="api_server")
        command = {"command": "python skills/email/scripts/email_tool.py list-unseen"}
        self.assertIsNone(plugin._on_pre_tool_call("terminal", command, session_id="web"))


if __name__ == "__main__":
    unittest.main()
