#!/usr/bin/env python3
"""Демонстрация LFS CORE v0.4"""
from lfs_core import autonomy as A
import pprint

print("=== Базовый тест (без смены законов) ===")
for cls in (A.Follower, A.FollowerRandomFallback, A.Explorer):
    res = A.evaluate(cls, change_at=None)
    print(f"{cls.__name__:25s} {res['verdict']:12s}  on={res['quality_on']:.3f}  off={res['quality_off']:.3f}  deg={res['degradation']:.3f}")

print("\n=== Тест со сменой законов в середине (t=18) ===")
for cls in (A.Follower, A.FollowerRandomFallback, A.Explorer):
    res = A.evaluate(cls, change_at=18)
    print(f"{cls.__name__:25s} {res['verdict']:12s}  on={res['quality_on']:.3f}  off={res['quality_off']:.3f}  deg={res['degradation']:.3f}")

print("\n=== Transfer-тест (новый размер мира + смена законов) ===")
for cls in (A.FollowerRandomFallback, A.Explorer):
    res = A.transfer_test(cls)
    print(f"{cls.__name__:25s} {res['verdict']:12s}  quality={res['quality_transfer']:.3f}  baseline={res['baseline_random']:.3f}")
