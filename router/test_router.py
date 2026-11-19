import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.execute import CloudHTTPError, execute
from router.router import CLOUD_MODEL, LOCAL_MODEL, Task, route


class RouteTests(unittest.TestCase):
    def test_simulated_rate_limit_never_calls_cloud(self):
        decision = route(Task("brief", simulate_rate_limit=True, local_up=True))
        self.assertEqual(decision.reason, "simulated_rate_limit")
        self.assertFalse(decision.call_cloud)
        self.assertEqual(decision.model, LOCAL_MODEL)

    def test_live_rate_limit_uses_local(self):
        decision = route(Task("brief", cloud_status=429, local_up=True))
        self.assertEqual(decision.reason, "cloud_rate_limit")
        self.assertEqual(decision.model, LOCAL_MODEL)

    def test_cloud_404_uses_local(self):
        decision = route(Task("brief", cloud_status=404, local_up=True))
        self.assertEqual(decision.reason, "cloud_model_unavailable")
        self.assertFalse(decision.call_cloud)

    def test_privacy_prefers_local(self):
        decision = route(Task("rewrite", privacy=True, simple=True, local_up=True))
        self.assertEqual(decision.reason, "privacy")
        self.assertEqual(decision.model, LOCAL_MODEL)

    def test_simple_uses_local(self):
        decision = route(Task("summarize", simple=True, local_up=True))
        self.assertEqual(decision.reason, "simple")

    def test_reasoning_uses_cloud(self):
        decision = route(Task("brief", local_up=True))
        self.assertEqual(decision.reason, "reasoning")
        self.assertEqual(decision.model, CLOUD_MODEL)
        self.assertTrue(decision.call_cloud)

    def test_local_down_for_simple_task_uses_cloud(self):
        decision = route(Task("summarize", simple=True, local_up=False))
        self.assertEqual(decision.reason, "local_unavailable")
        self.assertEqual(decision.model, CLOUD_MODEL)

    def test_privacy_that_does_not_fit_uses_cloud(self):
        decision = route(Task("rewrite", privacy=True, fits_local_context=False, local_up=True))
        self.assertEqual(decision.reason, "reasoning")
        self.assertTrue(decision.call_cloud)

    def test_draft_and_plan_use_cloud(self):
        for kind in ("draft", "plan"):
            decision = route(Task(kind, local_up=True))
            self.assertEqual(decision.reason, "reasoning")
            self.assertEqual(decision.model, CLOUD_MODEL)


class ExecuteTests(unittest.TestCase):
    def test_every_policy_row_calls_only_the_chosen_backend(self):
        rows = [
            (Task("brief", simulate_rate_limit=True), "simulated_rate_limit", "local"),
            (Task("brief", cloud_status=429, local_up=True), "cloud_rate_limit", "local"),
            (Task("rewrite", privacy=True, fits_local_context=True, local_up=True), "privacy", "local"),
            (Task("summarize", simple=True, local_up=True), "simple", "local"),
            (Task("brief", local_up=True), "reasoning", "cloud"),
            (Task("summarize", simple=True, local_up=False), "local_unavailable", "cloud"),
            (Task("brief", cloud_status=404, local_up=True), "cloud_model_unavailable", "local"),
        ]
        for task, reason, side in rows:
            with self.subTest(reason=reason):
                outcome = self._run(task)
                self.assertEqual(outcome.reason, reason)
                self.assertEqual(outcome.model_requested, LOCAL_MODEL if side == "local" else CLOUD_MODEL)
                self.assertTrue(outcome.success)
                self.assertEqual(self.called, {side})

    def test_flag_file_keeps_a_short_task_off_openai(self):
        with TemporaryDirectory() as directory:
            flag = Path(directory) / "FORCE_LOCAL"
            flag.write_text("1\n", encoding="utf-8")
            outcome = self._run(Task("summarize", simple=True), flag_path=flag)
        self.assertEqual(outcome.reason, "simulated_rate_limit")
        self.assertEqual(self.called, {"local"})

    def test_env_flag_keeps_a_briefing_off_openai(self):
        outcome = self._run(Task("brief"), env={"SIMULATE_RATE_LIMIT": "1"})
        self.assertEqual(outcome.reason, "simulated_rate_limit")
        self.assertEqual(self.called, {"local"})

    def test_removing_the_flag_restores_cloud(self):
        with TemporaryDirectory() as directory:
            flag = Path(directory) / "FORCE_LOCAL"
            flag.write_text("1\n", encoding="utf-8")
            self._run(Task("brief"), flag_path=flag)
            flag.unlink()
            outcome = self._run(Task("brief"), flag_path=flag, env={})
        self.assertEqual(outcome.reason, "reasoning")
        self.assertEqual(self.called, {"cloud"})

    def test_live_429_falls_back_to_local_without_a_second_cloud_call(self):
        def cloud(prompt):
            self.called.add("cloud")
            raise CloudHTTPError(429)

        def local(prompt):
            self.called.add("local")
            return "local", LOCAL_MODEL

        self.called = set()
        with TemporaryDirectory() as directory:
            outcome = execute(
                Task("brief", local_up=True),
                "ping",
                cloud=cloud,
                local=local,
                log_path=Path(directory) / "router.log",
                flag_path=Path(directory) / "missing",
                env={},
            )
        self.assertEqual(outcome.reason, "cloud_rate_limit")
        self.assertEqual(self.called, {"cloud", "local"})

    def test_log_line_has_the_required_fields(self):
        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "router.log"
            self._run(Task("summarize", simple=True), log_path=log_path)
            row = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(
            set(row),
            {
                "component",
                "timestamp",
                "task_type",
                "reason",
                "target",
                "model_requested",
                "model_answered",
                "success",
                "latency_ms",
            },
        )
        self.assertEqual(row["component"], "lumen-router")
        self.assertEqual(row["target"], "local")
        self.assertNotIn("ping", json.dumps(row))

    def _run(self, task, flag_path=None, env=None, log_path=None):
        self.called = set()

        def cloud(prompt):
            self.called.add("cloud")
            return "cloud", CLOUD_MODEL

        def local(prompt):
            self.called.add("local")
            return "local", LOCAL_MODEL

        with TemporaryDirectory() as directory:
            return execute(
                task,
                "ping",
                cloud=cloud,
                local=local,
                log_path=log_path or Path(directory) / "router.log",
                flag_path=flag_path or Path(directory) / "missing",
                env={} if env is None else env,
            )


if __name__ == "__main__":
    unittest.main()
