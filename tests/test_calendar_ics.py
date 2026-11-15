import unittest
from datetime import datetime
from pathlib import Path

from lib.calendar_ics import conflicts, events_on, gaps, parse_ics

FIXTURE = Path(__file__).resolve().parents[1] / "synthetic" / "fixtures" / "calendar.ics"
DAY = datetime.fromisoformat("2026-11-15T08:00:00-08:00")


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.events = events_on(parse_ics(FIXTURE.read_text(encoding="utf-8")), DAY)

    def test_reads_timed_events_in_los_angeles(self):
        titles = [item.summary for item in self.events]
        self.assertEqual(titles, ["Seminar", "Review", "Overlap review"])

    def test_finds_the_intentional_conflict(self):
        pairs = conflicts(self.events)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0].summary, "Review")
        self.assertEqual(pairs[0][1].summary, "Overlap review")

    def test_afternoon_gap_is_at_least_90_minutes(self):
        open_slots = gaps(self.events, DAY)
        after_conflict = [slot for slot in open_slots if slot[0].hour >= 11]
        self.assertTrue(after_conflict)
        start, end = after_conflict[0]
        self.assertGreaterEqual((end - start).total_seconds(), 90 * 60)


if __name__ == "__main__":
    unittest.main()
