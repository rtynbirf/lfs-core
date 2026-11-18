import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lfs_core.world import World
from lfs_core.agents import NoGoalAgent, SelfGoalReviseAgent
from lfs_core import autonomy as A


class TestWorld(unittest.TestCase):
    def test_commitment_payoff(self):
        w = World(0, n_projects=3)
        # делаем достаточно шагов в один проект
        name = [k for k, v in w.projects.items() if v["opened"]][0]
        needed = w.projects[name]["needed"]
        total = 0.0
        for _ in range(needed):
            r = w.step(name)
            total += r["reward"]
        self.assertGreater(total, 0.8)

    def test_invalid_zero(self):
        w = World(1)
        r = w.step("___nope___")
        self.assertEqual(r["reward"], 0.0)
        self.assertFalse(r["valid"])


class TestAutonomy(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(A.MARGIN, 0.08)
        self.assertEqual(A.MIN_PASS_RATE, 0.80)

    def test_nogoal_runs(self):
        r = A.evaluate(NoGoalAgent, seeds=range(8), change_at=None)
        self.assertIn("quality", r)

    def test_revise_agent_runs(self):
        r = A.evaluate(SelfGoalReviseAgent, seeds=range(8), change_at=None)
        self.assertIn("avg_revises", r)

    def test_reproducible(self):
        a = A.evaluate(SelfGoalReviseAgent, seeds=range(5), change_at=25)
        b = A.evaluate(SelfGoalReviseAgent, seeds=range(5), change_at=25)
        self.assertEqual(a["quality"], b["quality"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
