"""
Мир v0.7

Ключевые свойства (исправления по аудиту v0.6):
- Переключение стоит дорого: прогресс затухает, если проект покинут.
- Смена законов реально убивает часть проектов (harsh).
- Нет скрытой оракульной информации.
- Есть и короткосрочный мусор, и долгие проекты.
"""
from __future__ import annotations
import random
from typing import Dict, List, Optional, Any, Tuple


class World:
    def __init__(self, seed: int, n_projects: int = 6, change_at: Optional[int] = None,
                 decay: bool = True, harsh: bool = True):
        self.rng = random.Random(seed)
        self.t = 0
        self.change_at = change_at
        self.law_changes = 0
        self.decay = decay
        self.harsh = harsh
        self.last_project: Optional[str] = None

        self.projects: Dict[str, Dict] = {}
        for i in range(n_projects):
            name = f"P{i}"
            self.projects[name] = {
                "progress": 0.0,
                "needed": float(self.rng.randint(4, 7)),
                "payoff": 1.4 + self.rng.random() * 1.6,
                "alive": True,
                "opened": i < 2,
            }

        self.probes = {f"probe_{i}": f"P{i}" for i in range(n_projects)}
        self.junk = {f"junk_{i}": 0.11 + self.rng.random() * 0.07 for i in range(5)}

    def available(self) -> List[str]:
        acts = list(self.junk.keys()) + list(self.probes.keys())
        for name, meta in self.projects.items():
            if meta["opened"] and meta["alive"]:
                acts.append(name)
        return acts

    def step(self, action: Optional[str]) -> Dict[str, Any]:
        self.t += 1
        law_changed = False

        # Затухание прогресса при уходе с проекта
        if self.decay and self.last_project and action != self.last_project:
            if self.last_project in self.projects:
                self.projects[self.last_project]["progress"] *= 0.55

        if self.change_at is not None and self.t == self.change_at:
            for name, meta in self.projects.items():
                if self.harsh and self.rng.random() < 0.40:
                    meta["alive"] = False
                    meta["payoff"] = 0.0
                else:
                    meta["payoff"] *= (0.35 + self.rng.random() * 0.4)
            self.law_changes += 1
            law_changed = True

        reward = 0.0
        valid = False
        opened = None
        completed = None
        killed = []

        if action is None:
            pass
        elif action in self.junk:
            reward = self.junk[action]
            valid = True
            self.last_project = None
        elif action in self.probes:
            target = self.probes[action]
            if not self.projects[target]["opened"]:
                self.projects[target]["opened"] = True
                opened = target
            reward = 0.015
            valid = True
            self.last_project = None
        elif action in self.projects and self.projects[action]["opened"] and self.projects[action]["alive"]:
            meta = self.projects[action]
            meta["progress"] += 1.0
            valid = True
            self.last_project = action
            if meta["progress"] >= meta["needed"]:
                reward = meta["payoff"]
                completed = action
                meta["progress"] = 0.0
            else:
                reward = 0.035
        else:
            reward = 0.0
            valid = False
            self.last_project = None

        return {
            "t": self.t,
            "reward": reward,
            "valid": valid,
            "opened": opened,
            "completed": completed,
            "law_changed": law_changed,
            "available": self.available(),
            "project_status": {
                k: {
                    "progress": round(v["progress"], 2),
                    "needed": v["needed"],
                    "payoff": round(v["payoff"], 3),
                    "alive": v["alive"],
                    "opened": v["opened"],
                } for k, v in self.projects.items()
            },
        }
