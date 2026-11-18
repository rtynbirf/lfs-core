"""
LFS CORE v0.7

Pre-registered (не менять):
  MARGIN = 0.10
  MIN_PASS_RATE = 0.90
  STEPS = 70
"""
from __future__ import annotations
import statistics
from typing import Type, Dict, Any, List, Optional
from .world import World
from .event import Event, Source, Kind
from .agents import (ReactiveAgent, StickyAgent, ExternalGoalAgent,
                     SelfGoalAgent, SelfGoalReviseAgent)


MARGIN = 0.10
MIN_PASS_RATE = 0.90
STEPS = 70


def run_episode(agent_cls: Type, seed: int, change_at: Optional[int] = None) -> Dict[str, Any]:
    world = World(seed, n_projects=6, change_at=change_at, decay=True, harsh=True)
    agent = agent_cls(seed)

    events: List[Event] = []
    total = 0.0
    goals = abandons = revises = completed = 0
    last_reward = last_opened = None

    for t in range(STEPS):
        # External goal: только имя случайного открытого живого проекта (без payoff)
        ext_goal = None
        if agent_cls is ExternalGoalAgent:
            live = [k for k, v in world.projects.items() if v["opened"] and v["alive"]]
            if live:
                ext_goal = live[seed % len(live)]   # детерминированный, но без знания ценности

        obs = {
            "t": t,
            "available": world.available(),
            "last_reward": last_reward,
            "opened": last_opened,
            "external_goal": ext_goal,
            "project_status": {k: dict(v) for k, v in world.projects.items()},
        }

        action, ginfo = agent.step(obs)

        if ginfo:
            k = ginfo.get("kind")
            if k == "goal":
                # harness проверяет, что target существует и открыт
                target = ginfo.get("target")
                if target in world.projects and world.projects[target]["opened"]:
                    events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL, ginfo))
                    goals += 1
                else:
                    events.append(Event(len(events), t, Source.UNKNOWN, Kind.GOAL, {**ginfo, "unverified": True}))
            elif k == "goal_abandon":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_ABANDON, ginfo))
                abandons += 1
            elif k == "goal_revise":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_REVISE, ginfo))
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
    }


def evaluate(agent_cls: Type, seeds=range(30), change_at: Optional[int] = None) -> Dict[str, Any]:
    results = [run_episode(agent_cls, s, change_at) for s in seeds]
    base = [run_episode(ReactiveAgent, s + 9000, change_at) for s in seeds]
    q = statistics.fmean(r["quality"] for r in results)
    b = statistics.fmean(r["quality"] for r in base)
    pr = sum(1 for r in results if r["quality"] >= b + MARGIN) / len(results)
    return {
        "quality": round(q, 3),
        "baseline_reactive": round(b, 3),
        "delta": round(q - b, 3),
        "pass_rate": round(pr, 3),
        "avg_goals": round(statistics.fmean(r["goals"] for r in results), 2),
        "avg_abandons": round(statistics.fmean(r["abandons"] for r in results), 2),
        "avg_revises": round(statistics.fmean(r["revises"] for r in results), 2),
        "avg_completed": round(statistics.fmean(r["completed"] for r in results), 2),
        "verdict": "NOT_REFUTED" if pr >= MIN_PASS_RATE else "REFUTED",
    }


def full_report(seeds=range(25), change_at: Optional[int] = 35) -> Dict[str, Any]:
    modes = [
        ("A_Reactive", ReactiveAgent),
        ("B_Sticky", StickyAgent),
        ("C_External", ExternalGoalAgent),
        ("D_SelfGoal", SelfGoalAgent),
        ("E_SelfRevise", SelfGoalReviseAgent),
    ]
    return {name: evaluate(cls, seeds=seeds, change_at=change_at) for name, cls in modes}
