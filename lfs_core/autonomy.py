"""
LFS CORE v0.6 — Goal Necessity & Causal Value

Pre-registered:
  margin = 0.08
  min_pass_rate = 0.80
  STEPS = 60

Четыре режима сравниваются на одном и том же мире.
"""
from __future__ import annotations
import statistics
from typing import Type, Dict, Any, List, Optional
from .world import World
from .event import Event, Source, Kind
from .agents import NoGoalAgent, ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent


MARGIN = 0.08
MIN_PASS_RATE = 0.80
STEPS = 60


def run_episode(agent_cls: Type,
                seed: int,
                change_at: Optional[int] = None,
                external_goal_policy: str = "best_open") -> Dict[str, Any]:
    world = World(seed, n_projects=5, change_at=change_at)
    agent = agent_cls(seed)

    events: List[Event] = []
    total = 0.0
    goals = 0
    abandons = 0
    revises = 0
    completed = 0
    last_reward = None
    last_opened = None

    for t in range(STEPS):
        # External goal injection for mode B
        ext_goal = None
        if agent_cls is ExternalGoalAgent:
            # простая политика: даём лучший открытый живой проект
            status = {k: v for k, v in world.projects.items() if v["opened"] and v["alive"]}
            if status:
                ext_goal = max(status.keys(), key=lambda k: status[k]["payoff"] - status[k]["progress"] * 0.05)

        obs = {
            "t": t,
            "available": world.available(),
            "last_reward": last_reward,
            "opened": last_opened,
            "external_goal": ext_goal,
            "project_status": {k: dict(v) for k, v in world.projects.items()},
        }

        action, goal_info = agent.step(obs)

        if goal_info:
            kind = goal_info.get("kind")
            if kind == "goal":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL, goal_info))
                goals += 1
            elif kind == "goal_abandon":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_ABANDON, goal_info))
                abandons += 1
            elif kind == "goal_revise":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_REVISE, goal_info))
                revises += 1

        result = world.step(action)
        last_reward = result["reward"]
        last_opened = result["opened"]
        total += result["reward"]
        if result["completed"]:
            completed += 1

        events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.ACTION,
                            {"action": action, "valid": result["valid"]}))

        if result["law_changed"]:
            events.append(Event(len(events), t, Source.PID0_ENV, Kind.LAW_CHANGE, {}))

    return {
        "quality": total / STEPS,
        "goals": goals,
        "abandons": abandons,
        "revises": revises,
        "completed": completed,
        "events": events,
    }


def evaluate(agent_cls: Type,
             seeds=range(28),
             change_at: Optional[int] = None) -> Dict[str, Any]:
    results = [run_episode(agent_cls, s, change_at=change_at) for s in seeds]
    base_res = [run_episode(NoGoalAgent, s + 7000, change_at=change_at) for s in seeds]

    q = statistics.fmean(r["quality"] for r in results)
    base = statistics.fmean(r["quality"] for r in base_res)
    pass_rate = sum(1 for r in results if r["quality"] >= base + MARGIN) / len(results)

    return {
        "quality": round(q, 3),
        "baseline_nogoal": round(base, 3),
        "delta": round(q - base, 3),
        "pass_rate": round(pass_rate, 3),
        "avg_goals": round(statistics.fmean(r["goals"] for r in results), 2),
        "avg_abandons": round(statistics.fmean(r["abandons"] for r in results), 2),
        "avg_revises": round(statistics.fmean(r["revises"] for r in results), 2),
        "avg_completed": round(statistics.fmean(r["completed"] for r in results), 2),
        "verdict": "NOT_REFUTED" if pass_rate >= MIN_PASS_RATE else "REFUTED",
        "change_at": change_at,
    }


def ablation_report(seeds=range(24), change_at: Optional[int] = 30) -> Dict[str, Any]:
    """Прямое сравнение четырёх режимов."""
    report = {}
    for name, cls in [
        ("A_NoGoal", NoGoalAgent),
        ("B_ExternalGoal", ExternalGoalAgent),
        ("C_SelfGoal", SelfGoalAgent),
        ("D_SelfGoalRevise", SelfGoalReviseAgent),
    ]:
        report[name] = evaluate(cls, seeds=seeds, change_at=change_at)
    return report
