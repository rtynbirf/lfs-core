import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lfs_core.world import World
from lfs_core.agents import StickyAgent, SelfGoalReviseAgent
from lfs_core import autonomy as A

class TestWorld(unittest.TestCase):
    def test_decay(self):
        w = World(0, decay=True)
        p = [k for k,v in w.projects.items() if v["opened"]][0]
        w.step(p); w.step(p)
        prog1 = w.projects[p]["progress"]
        w.step("junk_0")  # ушли
        self.assertLess(w.projects[p]["progress"], prog1)

    def test_harsh_kills(self):
        killed = 0
        for s in range(20):
            w = World(s, change_at=5, harsh=True)
            for _ in range(10):
                w.step("junk_0")
            killed += sum(1 for v in w.projects.values() if not v["alive"])
        self.assertGreater(killed, 0)

class TestAutonomy(unittest.TestCase):
    def test_thresholds_fixed(self):
        self.assertEqual(A.MARGIN, 0.10)
        self.assertEqual(A.MIN_PASS_RATE, 0.90)

    def test_runs(self):
        r = A.evaluate(StickyAgent, seeds=range(6), change_at=None)
        self.assertIn("quality", r)

    def test_revise_can_fire(self):
        # просто проверяем, что код не падает и структура на месте
        r = A.evaluate(SelfGoalReviseAgent, seeds=range(6), change_at=30)
        self.assertIn("avg_revises", r)

if __name__ == "__main__":
    unittest.main(verbosity=2)
