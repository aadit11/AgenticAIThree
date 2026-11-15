import unittest
from datetime import datetime
from pathlib import Path

from lib.calendar_ics import parse_ics
from lib.deadlines import load_deadlines, suggest_block, urgency

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.fromisoformat("2026-11-14T18:00:00-08:00")


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.items = load_deadlines(ROOT / "synthetic" / "deadlines.json")
        self.events = parse_ics((ROOT / "synthetic" / "fixtures" / "calendar.ics").read_text(encoding="utf-8"))

    def test_urgency_labels(self):
        labels = {item.title: urgency(item, NOW) for item in self.items}
        self.assertEqual(labels["Reading response"], "due_within_3_days")
        self.assertEqual(labels["Lab report"], "due_within_3_days")
        self.assertEqual(labels["System diagram"], "later")
        self.assertEqual(labels["Paper outline"], "submitted")

    def test_suggests_a_block_before_the_deadline(self):
        soon = next(item for item in self.items if item.title == "Reading response")
        block = suggest_block(self.events, soon, NOW)
        self.assertIsNotNone(block)
        start, end = block
        self.assertLess(start, soon.due)
        self.assertGreaterEqual((end - start).total_seconds(), 45 * 60)


if __name__ == "__main__":
    unittest.main()
