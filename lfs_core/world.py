"""
Мир v0.6 — спроектирован так, чтобы commitment имел цену и ценность.

Свойства:
- Проекты требуют нескольких последовательных вложений, прежде чем дают высокий payoff.
- Частая смена проектов (myopic) даёт низкий результат.
- Есть короткосрочный «мусор» с маленькой наградой.
- После смены законов некоторые проекты портятся.
- Открытие нового проекта требует dedicated probe-действий.
"""
from __future__ import annotations
import random
from typing import Dict, List, Optional, Any, Tuple


class World:
    def __init__(self, seed: int, n_projects: int = 5, change_at: Optional[int] = None,
                 decay: bool = False, harsh: bool = False):
        self.rng = random.Random(seed)
        self.t = -1            # v0.6.1: первый step() даёт t=0, смена ровно на change_at
        self.decay = decay     # v0.6.1: прогресс брошенного проекта теряется (реальная цена переключения)
        self.harsh = harsh     # v0.6.1: смена законов реально убивает часть проектов
        self.change_at = change_at
        self.law_changes = 0
        self.n_projects = n_projects

        # Проекты: требуют commitment_steps вложений, потом payoff
        self.projects: Dict[str, Dict] = {}
        for i in range(n_projects):
            name = f"P{i}"
            self.projects[name] = {
                "progress": 0,
                "needed": self.rng.randint(3, 6),
                "payoff": 1.2 + self.rng.random() * 1.8,   # высокий, но отложенный
                "alive": True,
                "opened": i < 2,   # первые два открыты сразу
            }

        # Probe-действия открывают закрытые проекты
        self.probes = {f"probe_{i}": f"P{i}" for i in range(n_projects)}

        # Короткосрочный мусор
        self.junk = {f"junk_{i}": 0.12 + self.rng.random() * 0.08 for i in range(4)}

        self.history: List[Tuple[int, str, float]] = []

    def available(self) -> List[str]:
        acts = list(self.junk.keys())
        acts += [p for p, meta in self.probes.items()]
        for name, meta in self.projects.items():
            if meta["opened"] and meta["alive"]:
                acts.append(name)
        return acts

    def step(self, action: Optional[str]) -> Dict[str, Any]:
        self.t += 1
        law_changed = False
        if self.change_at is not None and self.t == self.change_at:
            # Портим часть проектов
            for name, meta in self.projects.items():
                if self.rng.random() < 0.45:
                    if self.harsh:
                        meta["payoff"], meta["alive"] = 0.0, False
                    else:
                        meta["payoff"] *= 0.25
                        meta["alive"] = meta["payoff"] > 0.3
            self.law_changes += 1
            law_changed = True

        reward = 0.0
        valid = False
        opened = None
        completed = None

        if action is None:
            pass
        elif action in self.junk:
            reward = self.junk[action]
            valid = True
        elif action in self.probes:
            target = self.probes[action]
            if not self.projects[target]["opened"]:
                self.projects[target]["opened"] = True
                opened = target
            reward = 0.02
            valid = True
        elif action in self.projects and self.projects[action]["opened"] and self.projects[action]["alive"]:
            meta = self.projects[action]
            meta["progress"] += 1
            valid = True
            if meta["progress"] >= meta["needed"]:
                reward = meta["payoff"]
                completed = action
                meta["progress"] = 0   # можно повторять
            else:
                reward = 0.04   # маленький прогресс
        else:
            reward = 0.0
            valid = False

        if self.decay:
            for name, meta in self.projects.items():
                if name != action and meta["progress"] > 0:
                    meta["progress"] -= 1
        self.history.append((self.t, action, reward))
        return {
            "t": self.t,
            "reward": reward,
            "valid": valid,
            "opened": opened,
            "completed": completed,
            "law_changed": law_changed,
            "available": self.available(),
            "project_status": {k: {"progress": v["progress"], "needed": v["needed"],
                                   "payoff": round(v["payoff"], 2), "alive": v["alive"],
                                   "opened": v["opened"]}
                              for k, v in self.projects.items()},
        }
