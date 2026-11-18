#!/usr/bin/env python3
"""LFS CORE v0.6 — Goal Necessity ablation"""
from lfs_core import autonomy as A
from lfs_core.agents import NoGoalAgent, ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent

print("=== Pre-registered: margin=0.08, min_pass_rate=0.80, STEPS=60 ===\n")

print("--- Без смены законов ---")
for name, cls in [("A_NoGoal", NoGoalAgent), ("B_External", ExternalGoalAgent),
                  ("C_SelfGoal", SelfGoalAgent), ("D_SelfRevise", SelfGoalReviseAgent)]:
    r = A.evaluate(cls, change_at=None)
    print(f"{name:15s} {r['verdict']:12s}  q={r['quality']:.3f}  Δ={r['delta']:+.3f}  "
          f"goals={r['avg_goals']:.1f}  rev={r['avg_revises']:.1f}  done={r['avg_completed']:.1f}")

print("\n--- Со сменой законов (t=30) ---")
for name, cls in [("A_NoGoal", NoGoalAgent), ("B_External", ExternalGoalAgent),
                  ("C_SelfGoal", SelfGoalAgent), ("D_SelfRevise", SelfGoalReviseAgent)]:
    r = A.evaluate(cls, change_at=30)
    print(f"{name:15s} {r['verdict']:12s}  q={r['quality']:.3f}  Δ={r['delta']:+.3f}  "
          f"goals={r['avg_goals']:.1f}  rev={r['avg_revises']:.1f}  done={r['avg_completed']:.1f}")

print("\n--- Полный ablation report (change_at=30) ---")
rep = A.ablation_report(change_at=30)
for k, v in rep.items():
    print(f"{k:18s} q={v['quality']:.3f}  Δ={v['delta']:+.3f}  verdict={v['verdict']}")
