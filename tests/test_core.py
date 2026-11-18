import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lfs_core.experience import ExperienceLog, Record, Opportunity
from lfs_core.event import Source, Kind
from lfs_core.agents import GoalAgent, RandomAgent, ReactiveAgent, GreedyExplorer
from lfs_core import autonomy as A
from lfs_core.world import World


class SpoofGoals(RandomAgent):
    """Случайный агент, который каждый шаг заявляет цель на несуществующий канал."""
    def step(self, obs):
        a, _ = super().step(obs)
        return a, {"kind": "goal", "target": "res_999", "reason": "opened_channel:res_999", "born_t": obs["t"]}


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
        self.assertIn("idle", w.available_actions())
        r = w.step("___invalid___")
        self.assertFalse(r["valid"]); self.assertEqual(r["reward"], 0.0)

    def test_law_change_exactly_at_change_at(self):
        ep = A.run_episode(GoalAgent, 0, change_at=22)
        self.assertEqual([e.t for e in ep["events"] if e.kind is Kind.LAW_CHANGE], [22])


class TestGoalOrigin(unittest.TestCase):
    def test_every_goal_has_harness_parent(self):
        n = 0
        for s in range(30):
            ep = A.run_episode(GoalAgent, s)
            by_id = {e.id: e for e in ep["events"]}
            for g in (e for e in ep["events"] if e.kind is Kind.GOAL):
                n += 1
                self.assertEqual(len(g.parents), 1)
                p = by_id[g.parents[0]]
                self.assertIs(p.kind, Kind.CHANNEL_OPENED); self.assertIs(p.source, Source.PID0_ENV)
                self.assertEqual(p.payload, g.payload["target"]); self.assertLessEqual(p.t, g.t)
        self.assertGreater(n, 20)

    def test_spoofed_goals_are_not_counted(self):
        ep = A.run_episode(SpoofGoals, 1)
        self.assertEqual(ep["internal_goals"], 0); self.assertEqual(ep["unverified_goals"], A.STEPS)
        self.assertFalse(any(e.kind is Kind.GOAL for e in ep["events"]))


class TestAutonomy(unittest.TestCase):
    def test_random_and_reactive_refuted(self):
        for cls in (RandomAgent, ReactiveAgent):
            self.assertEqual(A.evaluate(cls, seeds=range(12))["verdict"], "REFUTED")

    def test_goal_agent_beats_random_on_fresh_seeds(self):
        for ch in (None, 22):
            r = A.evaluate(GoalAgent, seeds=range(100, 160), change_at=ch)
            self.assertGreaterEqual(r["pass_rate"], 0.90)     # строже pre-registered 0.85
            self.assertEqual(r["avg_unverified_goals"], 0.0)

    def test_known_limitation_goals_add_no_functional_value(self):
        for ch in (None, 22):
            self.assertEqual(A.goals_ablation(change_at=ch)["verdict"], "NO_FUNCTIONAL_VALUE")

    def test_known_limitation_high_reward_branch_is_dead(self):
        n = 0
        for s in range(20):
            ag, w = GoalAgent(s), World(s)
            last = op = None; av = w.available_actions()
            for t in range(A.STEPS):
                a, _ = ag.step({"t": t, "available": av, "last_reward": last, "opened": op})
                r = w.step(a); last, op, av = r["reward"], r["opened"], r["available"]
            n += sum(o.description.startswith("high_reward") for o in ag.log.opportunities)
        self.assertEqual(n, 0)    # цели порождаются только флагом opened от harness

    def test_thresholds_preregistered(self):
        self.assertEqual((A.MARGIN, A.MIN_PASS_RATE), (0.10, 0.85))

    def test_reproducible(self):
        self.assertEqual(A.evaluate(GoalAgent, seeds=range(6)), A.evaluate(GoalAgent, seeds=range(6)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
