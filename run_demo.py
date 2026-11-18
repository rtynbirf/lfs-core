#!/usr/bin/env python3
"""LFS CORE v0.6.1 — Goal Necessity ablation + контроли"""
from lfs_core import autonomy as A
from lfs_core.agents import (NoGoalAgent, ExternalGoalAgent, SelfGoalAgent, SelfGoalReviseAgent,
                             StickyHeuristic, OracleNoGoal)

MODES = [("A_NoGoal", NoGoalAgent), ("B_External(oracle)", ExternalGoalAgent), ("C_SelfGoal", SelfGoalAgent),
         ("D_SelfRevise", SelfGoalReviseAgent), ("Ctl_Sticky(no goals)", StickyHeuristic), ("Ceiling_Oracle", OracleNoGoal)]
print("=== Pre-registered: margin=0.08, min_pass_rate=0.80, STEPS=60 ===")
for label, kw, ch in (("default", {}, None), ("default+change30", {}, 30), ("harsh change30", dict(harsh=True), 30)):
    print(f"\n--- {label} ---")
    for name, cls in MODES:
        r = A.evaluate(cls, change_at=ch, **kw)
        print(f"{name:21s} {r['verdict']:12s} q={r['quality']:.3f} oracle%={r['share_of_oracle']:.2f} "
              f"post={r['post_change_quality']} done={r['avg_completed']:.1f} rev={r['avg_revises']:.1f}")
print("\n--- Прирост механизма целей над обязательством (StickyHeuristic) ---")
for name, cls in (("C", SelfGoalAgent), ("D", SelfGoalReviseAgent)):
    for ch in (None, 30):
        print(name, ch, A.goal_increment(cls, change_at=ch))
