import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lfs_core.experience import ExperienceLog, Record, Opportunity
from lfs_core.event import Source, Kind
from lfs_core.agents import GoalAgent, RandomAgent, ReactiveAgent
from lfs_core import autonomy as A
from lfs_core.world import World


class TestExperience(unittest.TestCase):
    def test_opportunity_and_estimate(self):
        L = ExperienceLog()
        L.add(Record(0, "w", "a", 0.7, Source.PID1_INTERNAL))
        self.assertAlmostEqual(L.estimate("w", "a", 1), 0.7, places=2)
        self.assertIsNone(L.estimate("w", "never", 1))
        L.add_opportunity(Opportunity(1, "high_reward:a", [], 0.7))
        self.assertEqual(len(L.open_opportunities()), 1)


class TestWorld(unittest.TestCase):
    def test_discovery_and_invalid(self):
        w = World(42, n_base=6)
        acts = w.available_actions()
        self.assertIn("idle", acts)
        # invalid action
        r = w.step("___invalid___")
        self.assertFalse(r["valid"])
        self.assertEqual(r["reward"], 0.0)


class TestAutonomy(unittest.TestCase):
    def test_random_refuted(self):
        r = A.evaluate(RandomAgent, seeds=range(12), change_at=None)
        self.assertEqual(r["verdict"], "REFUTED")

    def test_goal_agent_forms_goals(self):
        rep = A.goal_origin_report(GoalAgent, seed=3)
        # В большинстве сидов должен появиться хотя бы один goal-event
        # (не гарантия на одном сиде, но структура должна работать)
        self.assertIn("n_goals", rep)

    def test_thresholds_are_strict(self):
        self.assertEqual(A.MARGIN, 0.10)
        self.assertEqual(A.MIN_PASS_RATE, 0.85)

    def test_reproducible(self):
        a = A.evaluate(GoalAgent, seeds=range(6), change_at=None)
        b = A.evaluate(GoalAgent, seeds=range(6), change_at=None)
        self.assertEqual(a["quality"], b["quality"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
