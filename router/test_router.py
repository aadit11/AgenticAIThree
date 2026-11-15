import unittest

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


if __name__ == "__main__":
    unittest.main()
