import unittest

from router.classify import classify_turn, cloud_payload, has_tool_result
from router.router import route


class ClassifyTests(unittest.TestCase):
    def test_one_line_summary_is_local(self):
        task = classify_turn("Summarize this in one line: the lab meets Tuesday.", has_tool_followup=False)
        decision = route(task)
        self.assertEqual(decision.reason, "simple")
        self.assertEqual(decision.model, "gemma4:e2b")

    def test_private_note_is_local(self):
        task = classify_turn("Rewrite this marked private note: bring the draft.", has_tool_followup=False)
        decision = route(task)
        self.assertEqual(decision.reason, "privacy")

    def test_calendar_question_stays_on_the_cloud_model(self):
        task = classify_turn("What is on the calendar today?", has_tool_followup=False)
        decision = route(task)
        self.assertEqual(decision.reason, "reasoning")
        self.assertTrue(decision.call_cloud)

    def test_tool_followup_stays_on_the_cloud_model(self):
        task = classify_turn("Summarize this in one line: hello", has_tool_followup=True)
        decision = route(task)
        self.assertEqual(decision.reason, "reasoning")

    def test_tool_result_detection(self):
        self.assertTrue(has_tool_result([{"role": "assistant", "tool_calls": [{"id": "1"}]}]))
        self.assertFalse(has_tool_result([{"role": "user", "content": "hello"}]))

    def test_cloud_payload_renames_max_tokens(self):
        payload = cloud_payload(
            {
                "model": "something-else",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 40,
                "temperature": 0,
                "tools": [{"type": "function"}],
            }
        )
        self.assertEqual(payload["model"], "gpt-6.1-sol")
        self.assertEqual(payload["max_completion_tokens"], 40)
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("temperature", payload)
        self.assertIn("tools", payload)


if __name__ == "__main__":
    unittest.main()
