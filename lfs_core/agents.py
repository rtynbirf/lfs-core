"""
Пять режимов v0.7 (жёсткое разделение):

A. Reactive          — myopic, без упорства и без целей
B. Sticky            — упорство / commitment, без целей
C. ExternalGoal      — внешняя цель (без оракула)
D. SelfGoal          — самостоятельная цель, держит
E. SelfGoalRevise    — самостоятельная цель + пересмотр/отказ по ценности
"""
from __future__ import annotations
import random
from typing import Optional, Dict, Any, Tuple, List


class Base:
    def __init__(self, seed: int):
        self.rng = random.Random(seed + 23)
        self.mem: Dict[str, List[float]] = {}
        self.last = None
        self.t = 0

    def remember(self, a: str, r: float):
        self.mem.setdefault(a, []).append(r)

    def est(self, a: str) -> float:
        rs = self.mem.get(a, [])
        if not rs:
            return 0.0
        w = [0.65 ** i for i in range(len(rs))][::-1]
        return sum(x * ww for x, ww in zip(rs, w)) / sum(w)


class ReactiveAgent(Base):
    """A. Чистый myopic."""
    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last and obs.get("last_reward") is not None:
            self.remember(self.last, obs["last_reward"])
        acts = obs.get("available") or []
        if not acts:
            return None, None
        if self.rng.random() < 0.35:
            a = self.rng.choice(acts)
        else:
            a = max(acts, key=lambda x: self.est(x))
        self.last = a
        self.t = obs["t"]
        return a, None


class StickyAgent(Base):
    """B. Упорство без целей: доделывает начатый проект."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.current: Optional[str] = None
        self.steps = 0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last and obs.get("last_reward") is not None:
            self.remember(self.last, obs["last_reward"])
        acts = obs.get("available") or []
        status = obs.get("project_status") or {}

        # Если текущий проект ещё жив и не закончен — продолжаем
        if self.current and self.current in acts:
            st = status.get(self.current, {})
            if st.get("alive", True) and st.get("progress", 0) < st.get("needed", 99):
                self.steps += 1
                self.last = self.current
                self.t = obs["t"]
                return self.current, None

        # Иначе выбираем новый
        projects = [a for a in acts if a.startswith("P")]
        probes = [a for a in acts if a.startswith("probe")]
        if projects and self.rng.random() < 0.7:
            # предпочитаем уже начатые
            def score(a):
                st = status.get(a, {})
                return self.est(a) + 0.5 * (st.get("progress", 0) / max(1, st.get("needed", 1)))
            self.current = max(projects, key=score)
        elif probes and self.rng.random() < 0.4:
            self.current = self.rng.choice(probes)
        elif acts:
            self.current = max(acts, key=lambda x: self.est(x))
        else:
            self.current = None

        self.steps = 0
        self.last = self.current
        self.t = obs["t"]
        return self.current, None


class ExternalGoalAgent(Base):
    """C. Внешняя цель. Harness даёт только имя открытого проекта, без payoff."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.steps = 0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last and obs.get("last_reward") is not None:
            self.remember(self.last, obs["last_reward"])
        acts = obs.get("available") or []
        goal = obs.get("external_goal")  # только имя, без ценности

        if goal and goal in acts:
            self.steps += 1
            self.last = goal
            self.t = obs["t"]
            return goal, None

        # fallback
        a = max(acts, key=lambda x: self.est(x)) if acts else None
        self.steps = 0
        self.last = a
        self.t = obs["t"]
        return a, None


class SelfGoalAgent(Base):
    """D. Сам ставит цель и держит (без умного пересмотра)."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.goal: Optional[str] = None
        self.steps = 0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last and obs.get("last_reward") is not None:
            self.remember(self.last, obs["last_reward"])
        t = obs["t"]
        acts = obs.get("available") or []
        opened = obs.get("opened")
        status = obs.get("project_status") or {}
        ge = None

        if self.goal is None or self.goal not in acts or not status.get(self.goal, {}).get("alive", True):
            if opened:
                self.goal = opened
                self.steps = 0
                ge = {"kind": "goal", "target": opened, "reason": "opened", "born_t": t}
            else:
                cands = [a for a in acts if a.startswith("P")]
                if cands:
                    self.goal = max(cands, key=lambda a: self.est(a) + 0.3 * status.get(a, {}).get("progress", 0))
                    self.steps = 0
                    ge = {"kind": "goal", "target": self.goal, "reason": "self", "born_t": t}

        if self.goal and self.goal in acts and status.get(self.goal, {}).get("alive", True):
            self.steps += 1
            self.last = self.goal
            self.t = t
            return self.goal, ge

        # исследование
        probes = [a for a in acts if a.startswith("probe")]
        a = self.rng.choice(probes) if probes and self.rng.random() < 0.35 else (
            max(acts, key=lambda x: self.est(x)) if acts else None)
        self.last = a
        self.t = t
        return a, ge


class SelfGoalReviseAgent(Base):
    """E. Сам ставит + пересматривает + отказывается по наблюдаемой ценности."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.goal: Optional[str] = None
        self.steps = 0
        self.value_at_birth = 0.0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last and obs.get("last_reward") is not None:
            self.remember(self.last, obs["last_reward"])
        t = obs["t"]
        acts = obs.get("available") or []
        opened = obs.get("opened")
        status = obs.get("project_status") or {}
        ge = None

        # --- Пересмотр / отказ ---
        if self.goal:
            alive = status.get(self.goal, {}).get("alive", False)
            cur = self.est(self.goal)
            if not alive:
                ge = {"kind": "goal_abandon", "target": self.goal, "reason": "dead"}
                self.goal = None
                self.steps = 0
            else:
                # ищем заметно лучший живой проект
                alts = [a for a in acts if a.startswith("P") and a != self.goal
                        and status.get(a, {}).get("alive", True)]
                better = None
                best_v = cur + 0.22
                for a in alts:
                    v = self.est(a) + 0.25 * (status.get(a, {}).get("progress", 0) /
                                              max(1, status.get(a, {}).get("needed", 1)))
                    if v > best_v:
                        best_v, better = v, a
                if better:
                    ge = {"kind": "goal_revise", "from": self.goal, "to": better, "reason": "higher_value"}
                    self.goal = better
                    self.steps = 0
                    self.value_at_birth = best_v
                elif self.steps > 6 and cur < 0.06:
                    ge = {"kind": "goal_abandon", "target": self.goal, "reason": "low_value"}
                    self.goal = None
                    self.steps = 0
                elif self.steps > 18:
                    ge = {"kind": "goal_abandon", "target": self.goal, "reason": "timeout"}
                    self.goal = None
                    self.steps = 0

        # --- Формирование ---
        if self.goal is None:
            if opened and status.get(opened, {}).get("alive", True):
                self.goal = opened
                self.steps = 0
                self.value_at_birth = 0.4
                ge = {"kind": "goal", "target": opened, "reason": "opened", "born_t": t}
            else:
                cands = [a for a in acts if a.startswith("P") and status.get(a, {}).get("alive", True)]
                if cands:
                    def score(a):
                        st = status.get(a, {})
                        return self.est(a) + 0.45 * (st.get("progress", 0) / max(1, st.get("needed", 1)))
                    self.goal = max(cands, key=score)
                    self.steps = 0
                    self.value_at_birth = self.est(self.goal)
                    ge = {"kind": "goal", "target": self.goal, "reason": "value_select", "born_t": t}

        # --- Действие ---
        if self.goal and self.goal in acts and status.get(self.goal, {}).get("alive", True):
            self.steps += 1
            self.last = self.goal
            self.t = t
            return self.goal, ge

        probes = [a for a in acts if a.startswith("probe")]
        a = self.rng.choice(probes) if probes and self.rng.random() < 0.4 else (
            max(acts, key=lambda x: self.est(x)) if acts else None)
        self.last = a
        self.t = t
        return a, ge
