48-hour window: 2026-11-15 17:37:53 America/Los_Angeles through 2026-11-17 17:37:53 America/Los_Angeles.
UTC bounds: 2026-11-16T01:37:53Z through 2026-11-18T01:37:53Z.

journal.jsonl is the full-window job log: briefing, recap, alert, consolidate, and health.
jobs.json is the Cloud Storage copy of the schedule and last status.
cron-output/ is the saved job text. Hermes keeps the latest 50 files per job, so the earliest alert and health files live in the journal rather than as separate markdown.

Job ids:
  d80cdf6add03  lumen-briefing     08:00 America/Los_Angeles
  ccb81f5e4a6d  lumen-recap        21:00 America/Los_Angeles
  fcae0c6efff1  lumen-alerts       every 30 minutes
  c567f5363eab  lumen-consolidate  hourly at :15
  e53e8340045a  lumen-health       every 10 minutes

window-start.txt, restart-fact.txt, and MEMORY.md stayed on the bucket for the run.
gateway.log is the platform log. router.log and cloud-logging-router.json are routing decisions with no message text. No lumen-router line was written during the quiet window; those two files are the setup calls before it and the demo calls after it.
