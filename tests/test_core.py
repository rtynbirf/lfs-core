import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lfs_core.experience import ExperienceLog, Record
from lfs_core.event import Source
from lfs_core.verify import verify_model
from lfs_core import autonomy as A


class TestExperience(unittest.TestCase):
    def test_conflict_and_none(self):
        L = ExperienceLog(half_life=10)
        L.add(Record(0, "c", "a", 0.1, Source.PID0_ENV))
        L.add(Record(1, "c", "a", 0.9, Source.PID0_ENV))
        self.assertIn(("c", "a"), L.conflicts())
        self.assertIsNone(L.estimate("c", "never_seen", 5))


class TestVerify(unittest.TestCase):
    data = [("c", str(i % 6), (i % 6) / 6) for i in range(90)]

    def test_good_model_passes(self):
        def fit(tr):
            d = {a: y for _, a, y in tr}
            return lambda c, a: d.get(a)
        self.assertEqual(verify_model(fit, self.data)["verdict"], "PASS")

    def test_constant_fails(self):
        fit = lambda tr: (lambda c, a: 0.4)
        self.assertEqual(verify_model(fit, self.data)["verdict"], "FAIL")


class TestAutonomy(unittest.TestCase):
    def test_follower_refuted(self):
        r = A.evaluate(A.Follower, seeds=range(15), change_at=None)
        self.assertEqual(r["verdict"], "REFUTED")

    def test_random_refuted(self):
        r = A.evaluate(A.FollowerRandomFallback, seeds=range(15))
        self.assertEqual(r["verdict"], "REFUTED")

    def test_explorer_not_refuted_basic(self):
        r = A.evaluate(A.Explorer, seeds=range(20), change_at=None)
        self.assertEqual(r["verdict"], "NOT_REFUTED")
        self.assertLess(abs(r["degradation"]), 0.08)

    def test_explorer_with_law_change(self):
        r = A.evaluate(A.Explorer, seeds=range(20), change_at=16)
        # Даже при смене законов не должен полностью развалиться
        self.assertGreater(r["quality_off"], 0.45)

    def test_reproducible(self):
        a = A.evaluate(A.Explorer, seeds=range(8), change_at=12)
        b = A.evaluate(A.Explorer, seeds=range(8), change_at=12)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
