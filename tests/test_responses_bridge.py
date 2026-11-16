import unittest

from router.bridge import chat_from_responses, responses_request_from_chat


class BridgeTests(unittest.TestCase):
    def test_tool_turn_moves_to_the_responses_shape(self):
        payload = responses_request_from_chat(
            {
                "model": "other",
                "temperature": 0,
                "max_tokens": 40,
                "messages": [
                    {"role": "system", "content": "Be brief."},
                    {"role": "user", "content": "What is on the calendar?"},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "terminal", "arguments": "{\"command\":\"date\"}"},
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": "call_1", "content": "Sunday"},
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "terminal",
                            "description": "Run a command",
                            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
                        },
                    }
                ],
                "tool_choice": {"type": "function", "function": {"name": "terminal"}},
            }
        )
        self.assertEqual(payload["model"], "gpt-6.1-sol")
        self.assertEqual(payload["max_output_tokens"], 40)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["tools"][0]["name"], "terminal")
        self.assertNotIn("function", payload["tools"][0])
        self.assertEqual(payload["tool_choice"], {"type": "function", "name": "terminal"})
        kinds = [item.get("type") or item.get("role") for item in payload["input"]]
        self.assertEqual(kinds, ["system", "user", "function_call", "function_call_output"])

    def test_function_call_comes_back_as_a_chat_tool_call(self):
        chat = chat_from_responses(
            {
                "id": "resp_1",
                "model": "gpt-6.1-sol",
                "output": [
                    {"type": "reasoning", "summary": []},
                    {
                        "type": "function_call",
                        "call_id": "call_9",
                        "name": "terminal",
                        "arguments": "{\"command\":\"python calendar_tool.py\"}",
                    },
                ],
            }
        )
        message = chat["choices"][0]["message"]
        self.assertEqual(chat["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(message["tool_calls"][0]["id"], "call_9")
        self.assertEqual(message["tool_calls"][0]["function"]["name"], "terminal")
        self.assertIsNone(message["content"])

    def test_plain_text_comes_back_as_a_stop(self):
        chat = chat_from_responses(
            {
                "model": "gpt-6.1-sol",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Paper Lantern"}],
                    }
                ],
            }
        )
        self.assertEqual(chat["choices"][0]["finish_reason"], "stop")
        self.assertEqual(chat["choices"][0]["message"]["content"], "Paper Lantern")


if __name__ == "__main__":
    unittest.main()
