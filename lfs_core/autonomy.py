"""
LFS CORE v0.6.1 — Goal Necessity & Causal Value (патч v0.6 по аудиту, см. AUDIT.md)

Pre-registered (как в v0.6, не менялись): margin = 0.08, min_pass_rate = 0.80, STEPS = 60.
Критерий атрибуции (зафиксирован до запуска): механизм целей добавляет ценность, только если
q(режим) >= q(StickyHeuristic) + MARGIN при тех же наблюдениях и в том же мире.
"""
from __future__ import annotations
import statistics
from typing import Type, Dict, Any, List, Optional
from .world import World
from .event import Event, Source, Kind
from .agents import (NoGoalAgent, ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent,
                     StickyHeuristic, OracleNoGoal)

MARGIN = 0.08
MIN_PASS_RATE = 0.80
STEPS = 60


def _external_goal(world: World, policy: str, rng_state: Dict[str, Any]):
    live = [k for k, v in world.projects.items() if v["opened"] and v["alive"]]
    if not live:
        return None
    if policy == "random":      # непривилегированная внешняя цель
        cur = rng_state.get("goal")
        if cur not in live:
            import random
            rng_state["goal"] = random.Random(rng_state["seed"] + rng_state["n"]).choice(live)
            rng_state["n"] += 1
        return rng_state["goal"]
    # "oracle": лучший живой проект по ИСТИННОМУ payoff (привилегированная информация)
    return max(live, key=lambda k: world.projects[k]["payoff"] - world.projects[k]["progress"] * 0.05)


def run_episode(agent_cls: Type, seed: int, change_at: Optional[int] = None,
                external_goal_policy: str = "oracle",
                decay: bool = False, harsh: bool = False) -> Dict[str, Any]:
    world = World(seed, n_projects=5, change_at=change_at, decay=decay, harsh=harsh)
    agent = agent_cls(seed)
    events: List[Event] = []
    opened_ev: Dict[str, int] = {}                 # независимый журнал открытия проектов (пишет harness)
    total = post = 0.0
    goals = unverified = abandons = revises = completed = 0
    last_reward = last_opened = None
    available = world.available()
    rng_state = {"seed": seed, "n": 0}

    for t in range(STEPS):
        ext = _external_goal(world, external_goal_policy, rng_state) if agent_cls is ExternalGoalAgent else None
        obs = {"t": t, "available": available, "last_reward": last_reward, "opened": last_opened,
               "external_goal": ext, "project_status": {k: dict(v) for k, v in world.projects.items()}}
        action, gi = agent.step(obs)

        if gi:
            kind = gi.get("kind")
            if kind == "goal":
                tgt = gi.get("target")
                # v0.6.1: происхождение подтверждает harness, а не самоотчёт. Цель должна быть на доступном
                # проекте; причина «opened» должна совпадать с реальным событием открытия.
                ok = tgt in available and (gi.get("reason") != "opened" or tgt == last_opened)
                if ok:
                    par = (opened_ev[tgt],) if (gi.get("reason") == "opened" and tgt in opened_ev) else ()
                    events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL, gi, parents=par))
                    goals += 1
                else:
                    events.append(Event(len(events), t, Source.UNKNOWN, Kind.GOAL_UNVERIFIED, gi))
                    unverified += 1
            elif kind == "goal_abandon":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_ABANDON, gi)); abandons += 1
            elif kind == "goal_revise":
                events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.GOAL_REVISE, gi)); revises += 1

        result = world.step(action)
        last_reward, last_opened, available = result["reward"], result["opened"], result["available"]
        total += result["reward"]
        if change_at is not None and t >= change_at:
            post += result["reward"]
        if result["completed"]:
            completed += 1
        events.append(Event(len(events), t, Source.PID1_INTERNAL, Kind.ACTION,
                            {"action": action, "valid": result["valid"]}))
        if result["opened"]:
            opened_ev[result["opened"]] = len(events)
            events.append(Event(len(events), t, Source.PID0_ENV, Kind.PROJECT_OPENED, result["opened"]))
        if result["law_changed"]:
            events.append(Event(len(events), t, Source.PID0_ENV, Kind.LAW_CHANGE, {}))

    return {"quality": total / STEPS,
            "post_quality": (post / (STEPS - change_at)) if change_at is not None else None,
            "goals": goals, "unverified_goals": unverified, "abandons": abandons,
            "revises": revises, "completed": completed, "events": events}


def evaluate(agent_cls: Type, seeds=range(28), change_at: Optional[int] = None, **wk) -> Dict[str, Any]:
    res = [run_episode(agent_cls, s, change_at, **wk) for s in seeds]
    base = [run_episode(NoGoalAgent, s + 7000, change_at, **wk) for s in seeds]
    orc = [run_episode(OracleNoGoal, s, change_at, **wk)["quality"] for s in seeds]
    q = statistics.fmean(r["quality"] for r in res)
    b = statistics.fmean(r["quality"] for r in base)
    pr = sum(r["quality"] >= b + MARGIN for r in res) / len(res)
    post = [r["post_quality"] for r in res if r["post_quality"] is not None]
    f = lambda k: round(statistics.fmean(r[k] for r in res), 2)
    return {"quality": round(q, 3), "baseline_nogoal": round(b, 3), "delta": round(q - b, 3),
            "pass_rate": round(pr, 3), "share_of_oracle": round(q / statistics.fmean(orc), 3),
            "post_change_quality": round(statistics.fmean(post), 3) if post else None,
            "avg_goals": f("goals"), "avg_unverified_goals": f("unverified_goals"),
            "avg_abandons": f("abandons"), "avg_revises": f("revises"), "avg_completed": f("completed"),
            "verdict": "NOT_REFUTED" if pr >= MIN_PASS_RATE else "REFUTED", "change_at": change_at}


def goal_increment(agent_cls: Type, seeds=range(28), change_at: Optional[int] = None, **wk) -> Dict[str, Any]:
    """Даёт ли именно механизм целей ценность сверх обязательства (StickyHeuristic: те же наблюдения, без целей)?"""
    a = evaluate(agent_cls, seeds, change_at, **wk)["quality"]
    c = evaluate(StickyHeuristic, seeds, change_at, **wk)["quality"]
    return {"q": a, "q_sticky": c, "increment": round(a - c, 3),
            "verdict": "GOAL_MECHANISM_ADDS_VALUE" if a - c >= MARGIN else "NO_INCREMENT_OVER_COMMITMENT"}


def ablation_report(seeds=range(24), change_at: Optional[int] = 30, **wk) -> Dict[str, Any]:
    out = {}
    for name, cls in [("A_NoGoal", NoGoalAgent), ("B_ExternalGoal", ExternalGoalAgent),
                      ("C_SelfGoal", SelfGoalAgent), ("D_SelfGoalRevise", SelfGoalReviseAgent),
                      ("Ctl_StickyHeuristic", StickyHeuristic)]:
        out[name] = evaluate(cls, seeds, change_at, **wk)
    return out
