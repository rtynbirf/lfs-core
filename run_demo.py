#!/usr/bin/env python3
"""LFS CORE v0.5 — Goal Genesis demo"""
from lfs_core import autonomy as A
from lfs_core.agents import RandomAgent, ReactiveAgent, GoalAgent

print("=== Pre-registered thresholds: margin=0.10, min_pass_rate=0.85 ===\n")

print("--- Без смены законов ---")
for cls in (RandomAgent, ReactiveAgent, GoalAgent):
    r = A.evaluate(cls, change_at=None)
    print(f"{cls.__name__:15s} {r['verdict']:12s}  q={r['quality']:.3f}  base={r['baseline_random']:.3f}  "
          f"goals={r['avg_internal_goals']:.1f}  disc={r['avg_discovered']:.1f}")

print("\n--- Со сменой законов (t=22) ---")
for cls in (RandomAgent, ReactiveAgent, GoalAgent):
    r = A.evaluate(cls, change_at=22)
    print(f"{cls.__name__:15s} {r['verdict']:12s}  q={r['quality']:.3f}  base={r['baseline_random']:.3f}  "
          f"goals={r['avg_internal_goals']:.1f}  disc={r['avg_discovered']:.1f}")

print("\n--- Пример происхождения целей (GoalAgent, seed=7) ---")
rep = A.goal_origin_report(GoalAgent, seed=7)
print(f"goals formed: {rep['n_goals']}, abandoned: {rep['n_abandons']}, quality={rep['quality']}, discovered={rep['discovered']}")
for g in rep["goals"][:5]:
    print("  ", g)
