import sys, os, random, unittest
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
        self.assertTrue(L.stale(now=200))


class TestVerify(unittest.TestCase):
    data = [("c", str(i % 7), (i % 7) / 7) for i in range(100)]
    def test_good_model_passes(self):
        def fit(tr):
            d = {a: y for _, a, y in tr}
            return lambda c, a: d.get(a)
        self.assertEqual(verify_model(fit, self.data)["verdict"], "PASS")
    def test_constant_fails(self):
        self.assertEqual(verify_model(lambda tr: (lambda c, a: 0.43), self.data)["verdict"], "FAIL")
    def test_noise_memorizer_fails(self):      # вернули из v0.3: в v0.4 он пропал
        r = random.Random(1)
        noise = [("c", str(i), r.random()) for i in range(100)]
        def fit(tr):
            d = {a: y for _, a, y in tr}
            return lambda c, a: d.get(a, 0.0)
        self.assertEqual(verify_model(fit, noise)["verdict"], "FAIL")


class TestHarness(unittest.TestCase):
    def test_law_change_fires_exactly_at_change_at(self):
        ev = A.run_trial(A.Explorer, 0, False, change_at=18)["events"]
        self.assertEqual([e.t for e in ev if e.kind == "law_change"], [18])
    def test_invalid_actions_are_penalised(self):
        r = A.evaluate(A.FollowerRandomFallback)
        self.assertGreater(r["invalid_frac_off"], 0.4)
        self.assertLess(r["quality_off"], r["baseline_random_valid"] - 0.2)
    def test_origin_audit_independent(self):
        for cls in (A.Follower, A.FollowerRandomFallback, A.Explorer):
            for on in (True, False):
                self.assertEqual(A.audit_origin(A.run_trial(cls, 3, on, change_at=15)), [])
    def test_leak_check_discriminates(self):
        self.assertTrue(A.leak_check(A.Explorer, change_at=18))
        self.assertFalse(A.leak_check(A.Follower))


class TestAutonomy(unittest.TestCase):
    def test_follower_refuted(self):
        r = A.evaluate(A.Follower)
        self.assertEqual(r["verdict"], "REFUTED"); self.assertEqual(r["quality_off"], 0.0)
    def test_random_fallback_refuted(self):
        self.assertEqual(A.evaluate(A.FollowerRandomFallback)["verdict"], "REFUTED")
    def test_explorer_mean_beats_baseline(self):
        # уровень СРЕДНЕГО, не пер-сидового pass_rate: пер-сидовый критерий Explorer не проходит (см. AUDIT.md)
        for ch in (None, 18):
            r = A.evaluate(A.Explorer, change_at=ch)
            self.assertGreater(r["quality_off"], r["baseline_random_valid"] + 0.05)
    def test_known_limitation_other_laws(self):
        # зафиксированная слабость: на gradient/n=40 Explorer хуже случайного
        r = A.evaluate(A.Explorer, seeds=range(100, 130), n_cells=40, steps=45, change_at=22, kind="gradient")
        self.assertEqual(r["verdict"], "REFUTED"); self.assertLess(r["quality_off"], r["baseline_random_valid"])
    def test_reproducible(self):
        self.assertEqual(A.evaluate(A.Explorer, seeds=range(8), change_at=12),
                         A.evaluate(A.Explorer, seeds=range(8), change_at=12))


if __name__ == "__main__":
    unittest.main(verbosity=2)
