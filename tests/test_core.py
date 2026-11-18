import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lfs_core.experience import ExperienceLog, Record
from lfs_core.event import Source
from lfs_core.verify import verify_model
from lfs_core import autonomy as A


class TestExperience(unittest.TestCase):
    def test_conflict_and_stale(self):
        L = ExperienceLog(half_life=10)
        L.add(Record(0, "c", "a", 0.1, Source.PID0_ENV))
        L.add(Record(1, "c", "a", 0.9, Source.PID0_ENV))
        self.assertIn(("c", "a"), L.conflicts())
        self.assertTrue(L.stale(now=100))
        self.assertIsNone(L.estimate("c", "zzz", 1))   # нет опыта -> None, не выдумка


class TestVerify(unittest.TestCase):
    data = [("c", str(i % 7), (i % 7) / 7) for i in range(100)]
    def test_real_model_passes(self):
        def fit(tr):
            d = {a: y for _, a, y in tr}
            return lambda c, a: d.get(a)
        self.assertEqual(verify_model(fit, self.data)["verdict"], "PASS")
    def test_trivial_model_fails(self):   # ложный PASS: константа не должна проходить
        fit = lambda tr: (lambda c, a: 0.43)
        self.assertEqual(verify_model(fit, self.data)["verdict"], "FAIL")
    def test_noise_memorizer_fails(self):
        import random; r = random.Random(1)
        noise = [("c", str(i), r.random()) for i in range(100)]
        def fit(tr):
            d = {a: y for _, a, y in tr}
            return lambda c, a: d.get(a, 0.0)
        self.assertEqual(verify_model(fit, noise)["verdict"], "FAIL")


class TestAutonomy(unittest.TestCase):
    def test_follower_fails_off(self):
        r = A.evaluate(A.Follower)
        self.assertEqual(r["verdict"], "REFUTED"); self.assertGreater(r["degradation"], 0.5)
    def test_random_fallback_fails(self):   # самостоятельность без качества не проходит
        self.assertEqual(A.evaluate(A.FollowerRandomFallback)["verdict"], "REFUTED")
    def test_explorer_passes(self):
        r = A.evaluate(A.Explorer)
        self.assertEqual(r["verdict"], "NOT_REFUTED"); self.assertLess(abs(r["degradation"]), 0.05)
    def test_reproducible(self):
        self.assertEqual(A.evaluate(A.Explorer), A.evaluate(A.Explorer))


if __name__ == "__main__":
    unittest.main(verbosity=2)
