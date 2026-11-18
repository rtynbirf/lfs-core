#!/usr/bin/env python3
from lfs_core import autonomy as A
from lfs_core.agents import (ReactiveAgent, StickyAgent, ExternalGoalAgent,
                             SelfGoalAgent, SelfGoalReviseAgent)

print("=== LFS v0.7 | Pre-registered: margin=0.10, pass_rate=0.90, STEPS=70 ===\n")

print("--- change_at=None ---")
for name, cls in [("A_Reactive", ReactiveAgent), ("B_Sticky", StickyAgent),
                  ("C_External", ExternalGoalAgent), ("D_SelfGoal", SelfGoalAgent),
                  ("E_SelfRevise", SelfGoalReviseAgent)]:
    r = A.evaluate(cls, change_at=None)
    print(f"{name:14s} {r['verdict']:12s} q={r['quality']:.3f} Δ={r['delta']:+.3f} "
          f"goals={r['avg_goals']:.1f} rev={r['avg_revises']:.1f} abn={r['avg_abandons']:.1f} done={r['avg_completed']:.1f}")

print("\n--- change_at=35 (harsh) ---")
for name, cls in [("A_Reactive", ReactiveAgent), ("B_Sticky", StickyAgent),
                  ("C_External", ExternalGoalAgent), ("D_SelfGoal", SelfGoalAgent),
                  ("E_SelfRevise", SelfGoalReviseAgent)]:
    r = A.evaluate(cls, change_at=35)
    print(f"{name:14s} {r['verdict']:12s} q={r['quality']:.3f} Δ={r['delta']:+.3f} "
          f"goals={r['avg_goals']:.1f} rev={r['avg_revises']:.1f} abn={r['avg_abandons']:.1f} done={r['avg_completed']:.1f}")
