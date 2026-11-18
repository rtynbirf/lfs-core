"""
LFS CORE v0.5 — Goal Genesis Experiment

Фиксированные до эксперимента пороги (pre-registration):
- margin = 0.10
- min_pass_rate = 0.85
- Честная метрика: недопустимое действие = reward 0, шагчик шагов полный.
"""
from __future__ import annotations
import statistics
from typing import Type, Dict, Any, List, Optional
from .world import World
from .event import Event, Source, Kind
from .agents import RandomAgent, ReactiveAgent, GoalAgent


# --- Pre-registered thresholds ---
MARGIN = 0.10
MIN_PASS_RATE = 0.85
STEPS = 50


def run_episode(agent_cls: Type,
                seed: int,
                change_at: Optional[int] = None,
                n_base: int = 10) -> Dict[str, Any]:
    world = World(seed, n_base=n_base, change_at=change_at)
    agent = agent_cls(seed)

    events: List[Event] = []
    total_reward = 0.0
    internal_goals = 0
    abandoned_goals = 0
    discovered_channels = 0
    last_reward = None
    last_opened = None

    for t in range(STEPS):
        obs = {
            "t": t,
            "available": world.available_actions(),
            "last_reward": last_reward,
            "opened": last_opened,
        }
        action, goal_info = agent.step(obs)

        # --- Goal events (harness records origin) ---
        if goal_info:
            if goal_info.get("kind") == "goal":
                ev = Event(
                    id=len(events), t=t,
                    source=Source.PID1_INTERNAL,
                    kind=Kind.GOAL,
                    payload=goal_info,
                    parents=()
                )
                events.append(ev)
                internal_goals += 1
            elif goal_info.get("kind") == "goal_abandon":
                ev = Event(
                    id=len(events), t=t,
                    source=Source.PID1_INTERNAL,
                    kind=Kind.GOAL_ABANDON,
                    payload=goal_info,
                    parents=()
                )
                events.append(ev)
                abandoned_goals += 1

        # --- Action ---
        result = world.step(action)
        last_reward = result["reward"]
        last_opened = result["opened"]
        total_reward += result["reward"]   # честная метрика: invalid = 0

        if result["opened"]:
            discovered_channels += 1

        src = Source.PID1_INTERNAL if action is not None else Source.UNKNOWN
        events.append(Event(
            id=len(events), t=t,
            source=src,
            kind=Kind.ACTION,
            payload={"action": action, "valid": result["valid"]},
            parents=(events[-1].id,) if events else ()
        ))

        if result["law_changed"]:
            events.append(Event(
                id=len(events), t=t,
                source=Source.PID0_ENV,
                kind=Kind.LAW_CHANGE,
                payload={"law_changes": world.law_changes}
            ))

    quality = total_reward / STEPS
    return {
        "quality": quality,
        "internal_goals": internal_goals,
        "abandoned_goals": abandoned_goals,
        "discovered_channels": discovered_channels,
        "events": events,
        "law_changes": world.law_changes,
    }


def evaluate(agent_cls: Type,
             seeds=range(30),
             change_at: Optional[int] = None,
             n_base: int = 10) -> Dict[str, Any]:
    results = [run_episode(agent_cls, s, change_at=change_at, n_base=n_base) for s in seeds]
    base_results = [run_episode(RandomAgent, s + 5000, change_at=change_at, n_base=n_base) for s in seeds]

    q = statistics.fmean(r["quality"] for r in results)
    base = statistics.fmean(r["quality"] for r in base_results)
    pass_rate = sum(1 for r in results if r["quality"] >= base + MARGIN) / len(results)

    goals = statistics.fmean(r["internal_goals"] for r in results)
    abandons = statistics.fmean(r["abandoned_goals"] for r in results)
    discovered = statistics.fmean(r["discovered_channels"] for r in results)

    return {
        "baseline_random": round(base, 3),
        "quality": round(q, 3),
        "pass_rate": round(pass_rate, 3),
        "avg_internal_goals": round(goals, 2),
        "avg_abandoned": round(abandons, 2),
        "avg_discovered": round(discovered, 2),
        "verdict": "NOT_REFUTED" if pass_rate >= MIN_PASS_RATE else "REFUTED",
        "change_at": change_at,
    }


def goal_origin_report(agent_cls: Type = GoalAgent, seed: int = 0) -> Dict[str, Any]:
    """Отчёт о происхождении целей в одном эпизоде."""
    ep = run_episode(agent_cls, seed, change_at=22)
    goals = [e for e in ep["events"] if e.kind is Kind.GOAL]
    abandons = [e for e in ep["events"] if e.kind is Kind.GOAL_ABANDON]
    return {
        "n_goals": len(goals),
        "n_abandons": len(abandons),
        "goals": [e.payload for e in goals],
        "quality": round(ep["quality"], 3),
        "discovered": ep["discovered_channels"],
    }
