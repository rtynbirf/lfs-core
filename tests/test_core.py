import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lfs_core.world import World
from lfs_core.event import Kind, Source
from lfs_core.agents import (NoGoalAgent, ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent,
                             StickyHeuristic, OracleNoGoal)
from lfs_core import autonomy as A


class SpoofGoals(NoGoalAgent):
    """Агент без механизма целей, который каждый шаг заявляет цель на несуществующий проект."""
    def step(self, obs):
        a, _ = super().step(obs)
        return a, {"kind": "goal", "target": "P99", "reason": "opened", "born_t": obs["t"]}


def _two_open(w):
    a, b = [k for k, v in w.projects.items() if v["opened"]][:2]
    na, nb = w.projects[a]["needed"], w.projects[b]["needed"]
    inter, ia, ib = [], 0, 0
    while ia < na or ib < nb:
        if ia < na: inter.append(a); ia += 1
        if ib < nb: inter.append(b); ib += 1
    return [a] * na + [b] * nb, inter


def _reward(w, acts):
    return sum(w.step(x)["reward"] for x in acts)


class TestWorld(unittest.TestCase):
    def test_commitment_payoff(self):
        w = World(0, n_projects=3)
        name = [k for k, v in w.projects.items() if v["opened"]][0]
        self.assertGreater(sum(w.step(name)["reward"] for _ in range(w.projects[name]["needed"])), 0.8)

    def test_invalid_zero(self):
        r = World(1).step("___nope___")
        self.assertEqual(r["reward"], 0.0); self.assertFalse(r["valid"])

    def test_default_world_has_no_switching_cost(self):
        seq, inter = _two_open(World(0))
        self.assertAlmostEqual(_reward(World(0), seq), _reward(World(0), inter))   # прогресс не затухает

    def test_decay_world_punishes_switching(self):
        seq, inter = _two_open(World(0, decay=True))
        self.assertGreater(_reward(World(0, decay=True), seq), 3 * _reward(World(0, decay=True), inter))

    def test_law_change_exactly_at_change_at(self):
        ev = A.run_episode(SelfGoalReviseAgent, 0, change_at=30)["events"]
        self.assertEqual([e.t for e in ev if e.kind is Kind.LAW_CHANGE], [30])

    def test_default_change_kills_no_project(self):    # зафиксированное ограничение v0.6
        dead = 0
        for s in range(50):
            w = World(s, change_at=30)
            for _ in range(31): w.step("junk_0")
            dead += sum(not v["alive"] for v in w.projects.values())
        self.assertEqual(dead, 0)


class TestGoalOrigin(unittest.TestCase):
    def test_spoofed_goals_unverified(self):
        r = A.run_episode(SpoofGoals, 0)
        self.assertEqual(r["goals"], 0); self.assertEqual(r["unverified_goals"], A.STEPS)

    def test_opened_goals_have_harness_parent(self):
        n = 0
        for s in range(20):
            ev = A.run_episode(SelfGoalAgent, s)["events"]; by = {e.id: e for e in ev}
            for g in (e for e in ev if e.kind is Kind.GOAL and e.payload.get("reason") == "opened"):
                n += 1; p = by[g.parents[0]]
                self.assertIs(p.kind, Kind.PROJECT_OPENED); self.assertEqual(p.payload, g.payload["target"])
        self.assertGreater(n, 5)


class TestCausalValue(unittest.TestCase):
    def test_nogoal_is_myopic_strawman(self):
        r = A.evaluate(NoGoalAgent, seeds=range(20))
        self.assertLessEqual(r["avg_completed"], 1.5); self.assertLess(r["share_of_oracle"], 0.35)

    def test_goal_modes_beat_nogoal(self):
        for cls in (ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent):
            self.assertEqual(A.evaluate(cls)["verdict"], "NOT_REFUTED")

    def test_external_goal_is_privileged_information(self):
        b = A.evaluate(ExternalGoalAgent)["quality"]; o = A.evaluate(OracleNoGoal)["quality"]
        self.assertGreaterEqual(o, b - 0.02)    # безцелевой оракул не хуже B

    def test_no_increment_over_commitment(self):
        for cls in (SelfGoalAgent, SelfGoalReviseAgent):
            for ch in (None, 30):
                self.assertEqual(A.goal_increment(cls, change_at=ch)["verdict"], "NO_INCREMENT_OVER_COMMITMENT")

    def test_revise_agent_never_revises_and_gets_stuck_on_dead_goal(self):
        r = A.evaluate(SelfGoalReviseAgent, change_at=30)
        self.assertEqual(r["avg_revises"], 0.0); self.assertEqual(r["avg_abandons"], 0.0)
        d = A.evaluate(SelfGoalReviseAgent, change_at=30, harsh=True)["post_change_quality"]
        s = A.evaluate(StickyHeuristic, change_at=30, harsh=True)["post_change_quality"]
        self.assertLess(d, s)

    def test_thresholds_preregistered(self):
        self.assertEqual((A.MARGIN, A.MIN_PASS_RATE, A.STEPS), (0.08, 0.80, 60))

    def test_reproducible(self):
        self.assertEqual(A.evaluate(SelfGoalReviseAgent, seeds=range(5), change_at=25),
                         A.evaluate(SelfGoalReviseAgent, seeds=range(5), change_at=25))


if __name__ == "__main__":
    unittest.main(verbosity=2)
