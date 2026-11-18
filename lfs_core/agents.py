"""
Четыре режима для проверки причинной роли целей.

A. NoGoal          — чистый greedy / exploratory, без целей
B. ExternalGoal    — цели приходят извне (harness)
C. SelfGoal        — агент сам формирует цели и держит их
D. SelfGoalRevise  — формирует + пересматривает + отказывается по ценности
"""
from __future__ import annotations
import random
from typing import Optional, Dict, Any, Tuple, List
from .event import Source


class BaseAgent:
    def __init__(self, seed: int):
        self.rng = random.Random(seed + 17)
        self.t = 0
        self.last_action = None
        self.memory: Dict[str, List[float]] = {}   # action -> list of rewards

    def _remember(self, action: str, reward: float):
        self.memory.setdefault(action, []).append(reward)

    def _est(self, action: str) -> float:
        rs = self.memory.get(action, [])
        if not rs:
            return 0.0
        # недавние важнее
        w = [0.7 ** i for i in range(len(rs))][::-1]
        return sum(r * ww for r, ww in zip(rs, w)) / sum(w)

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        raise NotImplementedError


class NoGoalAgent(BaseAgent):
    """A. Нет механизма целей. Myopic + лёгкое исследование."""
    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last_action is not None and obs.get("last_reward") is not None:
            self._remember(self.last_action, obs["last_reward"])
        acts = obs.get("available") or []
        if not acts:
            return None, None

        # ε-greedy
        if self.rng.random() < 0.28:
            action = self.rng.choice(acts)
        else:
            best, best_v = None, -1e9
            for a in acts:
                v = self._est(a)
                if v > best_v:
                    best_v, best = v, a
            action = best if best is not None else self.rng.choice(acts)

        self.last_action = action
        self.t = obs["t"]
        return action, None


class ExternalGoalAgent(BaseAgent):
    """B. Цели задаёт harness через obs['external_goal']."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.steps_on_goal = 0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last_action is not None and obs.get("last_reward") is not None:
            self._remember(self.last_action, obs["last_reward"])

        acts = obs.get("available") or []
        goal = obs.get("external_goal")
        goal_event = None

        if goal and goal in acts:
            action = goal
            self.steps_on_goal += 1
        else:
            # fallback как NoGoal
            if self.rng.random() < 0.3 or not acts:
                action = self.rng.choice(acts) if acts else None
            else:
                best = max(acts, key=lambda a: self._est(a))
                action = best
            self.steps_on_goal = 0

        self.last_action = action
        self.t = obs["t"]
        return action, goal_event


class SelfGoalAgent(BaseAgent):
    """C. Сам формирует цель и держит её фиксированное время."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.current_goal: Optional[str] = None
        self.goal_born = 0
        self.steps_on_goal = 0
        self.goal_history = []

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last_action is not None and obs.get("last_reward") is not None:
            self._remember(self.last_action, obs["last_reward"])

        t = obs["t"]
        acts = obs.get("available") or []
        opened = obs.get("opened")
        goal_event = None

        # Формируем цель при открытии или если нет цели
        if self.current_goal is None or self.current_goal not in acts:
            candidates = [a for a in acts if a.startswith("P")]
            if opened:
                self.current_goal = opened
                self.goal_born = t
                self.steps_on_goal = 0
                goal_event = {"kind": "goal", "target": opened, "reason": "opened", "born_t": t}
            elif candidates and self.rng.random() < 0.4:
                # выбираем по текущей оценке
                target = max(candidates, key=lambda a: self._est(a) + self.rng.random() * 0.1)
                self.current_goal = target
                self.goal_born = t
                self.steps_on_goal = 0
                goal_event = {"kind": "goal", "target": target, "reason": "self_select", "born_t": t}

        # Держим цель
        if self.current_goal and self.current_goal in acts and self.steps_on_goal < 12:
            action = self.current_goal
            self.steps_on_goal += 1
        else:
            if self.current_goal and self.steps_on_goal >= 12:
                goal_event = {"kind": "goal_abandon", "target": self.current_goal, "reason": "timeout"}
                self.goal_history.append(self.current_goal)
                self.current_goal = None
            # исследование / greedy
            probes = [a for a in acts if a.startswith("probe")]
            if probes and self.rng.random() < 0.35:
                action = self.rng.choice(probes)
            elif acts:
                action = max(acts, key=lambda a: self._est(a))
            else:
                action = None
            self.steps_on_goal = 0

        self.last_action = action
        self.t = t
        return action, goal_event


class SelfGoalReviseAgent(BaseAgent):
    """D. Формирует, пересматривает по ценности и отказывается."""
    def __init__(self, seed: int):
        super().__init__(seed)
        self.current_goal: Optional[str] = None
        self.goal_born = 0
        self.steps_on_goal = 0
        self.goal_value_at_birth = 0.0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        if self.last_action is not None and obs.get("last_reward") is not None:
            self._remember(self.last_action, obs["last_reward"])

        t = obs["t"]
        acts = obs.get("available") or []
        opened = obs.get("opened")
        status = obs.get("project_status") or {}
        goal_event = None

        # Пересмотр / отказ
        if self.current_goal:
            cur_est = self._est(self.current_goal)
            # ищем заметно лучшую альтернативу
            alts = [a for a in acts if a.startswith("P") and a != self.current_goal]
            better = None
            better_v = cur_est + 0.25
            for a in alts:
                v = self._est(a)
                if v > better_v:
                    better_v, better = v, a
            if better:
                goal_event = {"kind": "goal_revise", "from": self.current_goal, "to": better, "reason": "higher_value"}
                self.current_goal = better
                self.goal_born = t
                self.steps_on_goal = 0
                self.goal_value_at_birth = better_v
            elif self.steps_on_goal > 5 and cur_est < 0.08:
                goal_event = {"kind": "goal_abandon", "target": self.current_goal, "reason": "low_value"}
                self.current_goal = None
                self.steps_on_goal = 0
            elif self.steps_on_goal > 16:
                goal_event = {"kind": "goal_abandon", "target": self.current_goal, "reason": "timeout"}
                self.current_goal = None
                self.steps_on_goal = 0

        # Формирование новой цели
        if self.current_goal is None:
            if opened:
                self.current_goal = opened
                self.goal_born = t
                self.goal_value_at_birth = 0.5
                goal_event = {"kind": "goal", "target": opened, "reason": "opened", "born_t": t}
            else:
                candidates = [a for a in acts if a.startswith("P")]
                if candidates:
                    # предпочитаем проекты с прогрессом или высокой оценкой
                    def score(a):
                        st = status.get(a, {})
                        prog = st.get("progress", 0) / max(1, st.get("needed", 1))
                        return self._est(a) + 0.4 * prog
                    target = max(candidates, key=score)
                    self.current_goal = target
                    self.goal_born = t
                    self.goal_value_at_birth = self._est(target)
                    goal_event = {"kind": "goal", "target": target, "reason": "value_select", "born_t": t}

        # Действие
        if self.current_goal and self.current_goal in acts:
            action = self.current_goal
            self.steps_on_goal += 1
        else:
            probes = [a for a in acts if a.startswith("probe")]
            if probes and self.rng.random() < 0.4:
                action = self.rng.choice(probes)
            elif acts:
                action = max(acts, key=lambda a: self._est(a))
            else:
                action = None
            self.steps_on_goal = 0

        self.last_action = action
        self.t = t
        return action, goal_event
