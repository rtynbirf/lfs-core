"""
Мир v0.5 — без заранее заданной задачи.

Свойства:
- Несколько возможных «направлений» (каналов).
- Часть действий бесполезна.
- Часть действий открывает новые каналы (discovery).
- Законы могут меняться.
- Нет внешней инструкции «что делать».
"""
from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple, Any


class World:
    def __init__(self, seed: int, n_base: int = 10, change_at: Optional[int] = None):
        self.rng = random.Random(seed)
        self.t = -1          # v0.5.1: первый step() даёт t=0, смена ровно на change_at
        self.change_at = change_at
        self.law_changes = 0

        # Базовые каналы (всегда доступны)
        self.channels: Dict[str, Dict[str, float]] = {
            "idle": {"value": 0.05, "cost": 0.0, "opens": None},
            "noise": {"value": 0.02, "cost": 0.0, "opens": None},
        }

        # Полезные, но скрытые до обнаружения
        self.hidden: Dict[str, Dict[str, float]] = {}
        for i in range(n_base):
            name = f"res_{i}"
            self.hidden[name] = {
                "value": 0.3 + self.rng.random() * 0.55,
                "cost": 0.05 + self.rng.random() * 0.1,
                "opens": None,
            }

        # Действия-открыватели: некоторые «бесполезные» действия могут открыть канал
        self.discoverers: Dict[str, str] = {}
        hidden_names = list(self.hidden.keys())
        self.rng.shuffle(hidden_names)
        for i, name in enumerate(hidden_names[: max(3, n_base // 3)]):
            disc = f"probe_{i}"
            self.discoverers[disc] = name
            self.channels[disc] = {"value": 0.01, "cost": 0.08, "opens": name}

        # Бесполезные действия
        for i in range(6):
            self.channels[f"junk_{i}"] = {"value": 0.0, "cost": 0.03, "opens": None}

        self.opened: set = set()
        self.history: List[Tuple[int, str, float]] = []

    def available_actions(self) -> List[str]:
        acts = list(self.channels.keys())
        for name in self.opened:
            if name in self.hidden:
                acts.append(name)
        return acts

    def step(self, action: Optional[str]) -> Dict[str, Any]:
        self.t += 1
        law_changed = False
        if self.change_at is not None and self.t == self.change_at:
            # Меняем ценности открытых ресурсов
            for name in list(self.hidden.keys()):
                if name in self.opened or name in self.hidden:
                    self.hidden[name]["value"] = max(0.0, self.hidden[name]["value"] + self.rng.uniform(-0.35, 0.35))
            self.law_changes += 1
            law_changed = True

        reward = 0.0
        opened_new = None
        valid = False

        if action is None:
            reward = 0.0
        elif action in self.channels:
            meta = self.channels[action]
            reward = meta["value"] - meta["cost"]
            valid = True
            if meta["opens"] and meta["opens"] not in self.opened:
                self.opened.add(meta["opens"])
                opened_new = meta["opens"]
        elif action in self.opened and action in self.hidden:
            meta = self.hidden[action]
            reward = meta["value"] - meta["cost"]
            valid = True
        else:
            # недопустимое действие
            reward = 0.0
            valid = False

        self.history.append((self.t, action, reward))
        return {
            "t": self.t,
            "reward": reward,
            "valid": valid,
            "opened": opened_new,
            "law_changed": law_changed,
            "available": self.available_actions(),
        }

    def true_best_open(self) -> Optional[str]:
        best, best_v = None, -1e9
        for a in self.available_actions():
            if a in self.channels:
                v = self.channels[a]["value"] - self.channels[a]["cost"]
            elif a in self.hidden:
                v = self.hidden[a]["value"] - self.hidden[a]["cost"]
            else:
                continue
            if v > best_v:
                best_v, best = v, a
        return best
