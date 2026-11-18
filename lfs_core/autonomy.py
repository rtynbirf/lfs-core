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
from .agents import RandomAgent, ReactiveAgent, GoalAgent, GreedyExplorer


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
    opened_ev: Dict[str, int] = {}          # НЕЗАВИСИМЫЙ журнал: канал -> id события открытия (пишет harness)
    total_reward = post_reward = 0.0
    internal_goals = unverified_goals = abandoned_goals = discovered_channels = 0
    last_reward = None
    last_opened = None
    available = world.available_actions()

    for t in range(STEPS):
        obs = {"t": t, "available": available, "last_reward": last_reward, "opened": last_opened}
        action, goal_info = agent.step(obs)

        if goal_info:
            kind = goal_info.get("kind")
            if kind == "goal":
                # v0.5.1: происхождение цели подтверждает harness по своему журналу, а не по самоотчёту.
                tgt = goal_info.get("target")
                verified = (tgt in opened_ev and tgt in available
                            and goal_info.get("reason") == f"opened_channel:{tgt}")
                if verified:
                    events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL, goal_info,
                                        parents=(opened_ev[tgt],)))
                    internal_goals += 1
                else:
                    events.append(Event(len(events), t, Source.UNKNOWN, Kind.GOAL_UNVERIFIED, goal_info))
                    unverified_goals += 1
            elif kind == "goal_abandon":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_ABANDON, goal_info))
                abandoned_goals += 1

        result = world.step(action)
        last_reward, last_opened = result["reward"], result["opened"]
        available = result["available"]
        total_reward += result["reward"]
        if change_at is not None and t >= change_at:
            post_reward += result["reward"]

        src = Source.PID1_INTERNAL if action is not None else Source.UNKNOWN
        events.append(Event(len(events), t, src, Kind.ACTION,
                            {"action": action, "valid": result["valid"]},
                            parents=(events[-1].id,) if events else ()))
        if result["opened"]:
            discovered_channels += 1
            opened_ev[result["opened"]] = len(events)
            events.append(Event(len(events), t, Source.PID0_ENV, Kind.CHANNEL_OPENED, result["opened"],
                                parents=(events[-1].id,)))
        if result["law_changed"]:
            events.append(Event(len(events), t, Source.PID0_ENV, Kind.LAW_CHANGE,
                                {"law_changes": world.law_changes}))

    return {
        "quality": total_reward / STEPS,
        "post_quality": (post_reward / (STEPS - change_at)) if change_at is not None else None,
        "internal_goals": internal_goals,
        "unverified_goals": unverified_goals,
        "abandoned_goals": abandoned_goals,
        "discovered_channels": discovered_channels,
        "events": events,
        "law_changes": world.law_changes,
    }


def oracle_quality(seed: int, change_at: Optional[int] = None, n_base: int = 10) -> float:
    """Потолок: сразу открыть все каналы-открыватели, затем брать лучший доступный."""
    w = World(seed, n_base=n_base, change_at=change_at)
    plan = [a for a in w.channels if a.startswith("probe_")]
    tot = 0.0
    for _ in range(STEPS):
        a = plan.pop(0) if plan else w.true_best_open()
        tot += w.step(a)["reward"]
    return tot / STEPS


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
    unver = statistics.fmean(r["unverified_goals"] for r in results)
    orc = statistics.fmean(oracle_quality(s, change_at, n_base) for s in seeds)
    post = [r["post_quality"] for r in results if r["post_quality"] is not None]

    return {
        "baseline_random": round(base, 3),
        "quality": round(q, 3),
        "pass_rate": round(pass_rate, 3),
        "avg_internal_goals": round(goals, 2),
        "avg_abandoned": round(abandons, 2),
        "avg_discovered": round(discovered, 2),
        "avg_unverified_goals": round(unver, 2),
        "share_of_oracle": round(q / orc, 3),
        "post_change_quality": round(statistics.fmean(post), 3) if post else None,
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


def goals_ablation(seeds=range(30), change_at: Optional[int] = None) -> Dict[str, Any]:
    """Дают ли цели функциональную пользу? GoalAgent против GreedyExplorer (те же сенсоры, без целей).
    Критерий зафиксирован: цели полезны, только если q_goal >= q_greedy + MARGIN."""
    g = evaluate(GoalAgent, seeds, change_at)
    c = evaluate(GreedyExplorer, seeds, change_at)
    d = g["quality"] - c["quality"]
    return {"q_goal": g["quality"], "q_greedy": c["quality"], "delta": round(d, 3),
            "verdict": "GOALS_ADD_VALUE" if d >= MARGIN else "NO_FUNCTIONAL_VALUE"}
