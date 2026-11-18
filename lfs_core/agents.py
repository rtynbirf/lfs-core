"""
Агенты v0.5.

Ключевое отличие:
- Нет внешней инструкции «что делать».
- GoalAgent должен сам обнаруживать возможности,
  формулировать цели, фиксировать их происхождение,
  преследовать, пересматривать или отказываться.
"""
from __future__ import annotations
import random
from typing import Optional, List, Dict, Any, Tuple
from .experience import ExperienceLog, Record, Opportunity
from .event import Source


class RandomAgent:
    """Контроль: действует случайно среди доступных."""
    def __init__(self, seed: int):
        self.rng = random.Random(seed + 3)

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        acts = obs.get("available") or []
        if not acts:
            return None, None
        return self.rng.choice(acts), None


class ReactiveAgent:
    """
    Эксплуатирует уже известные действия по опыту.
    Не порождает явных целей. Не исследует активно.
    """
    def __init__(self, seed: int):
        self.log = ExperienceLog()
        self.rng = random.Random(seed + 11)
        self.last_action: Optional[str] = None
        self.t = 0

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        t = obs["t"]
        reward = obs.get("last_reward")
        if self.last_action is not None and reward is not None:
            self.log.add(Record(t - 1, "w", self.last_action, reward, Source.PID1_INTERNAL))

        acts = obs.get("available") or []
        if not acts:
            return None, None

        # Выбираем лучшее по текущей оценке, иначе случайное
        best, best_v = None, -1e9
        for a in acts:
            est = self.log.estimate("w", a, t)
            if est is not None and est > best_v:
                best_v, best = est, a
        if best is None or self.rng.random() < 0.25:
            best = self.rng.choice(acts)

        self.last_action = best
        self.t = t
        return best, None


class GoalAgent:
    """
    Цель: продемонстрировать Goal Genesis.

    Поведение:
    1. Собирает опыт.
    2. Обнаруживает возможности (высокий неожиданный reward или открытие канала).
    3. Формулирует явную цель (dict с kind="goal").
    4. Преследует текущую цель.
    5. Может отказаться от цели, если она перестала приносить ценность.
    6. Может пересмотреть цель при появлении лучшей возможности.
    """
    def __init__(self, seed: int):
        self.log = ExperienceLog(half_life=55.0)
        self.rng = random.Random(seed + 29)
        self.t = 0
        self.last_action: Optional[str] = None
        self.current_goal: Optional[Dict] = None   # {"target": str, "reason": str, "born_t": int, "evidence": list}
        self.goal_history: List[Dict] = []
        self.explored: set = set()
        self.steps_on_goal = 0

    def _record(self, t: int, action: str, reward: float):
        self.log.add(Record(t, "w", action, reward, Source.PID1_INTERNAL))

    def _detect_opportunity(self, action: str, reward: float, opened: Optional[str], t: int) -> Optional[Opportunity]:
        # Сильный положительный исход или открытие нового канала
        if opened:
            opp = Opportunity(
                t=t,
                description=f"opened_channel:{opened}",
                evidence=[],
                estimated_value=0.6,
                status="open"
            )
            self.log.add_opportunity(opp)
            return opp
        if reward > 0.35 and action not in self.explored:
            opp = Opportunity(
                t=t,
                description=f"high_reward:{action}",
                evidence=[],
                estimated_value=reward,
                status="open"
            )
            self.log.add_opportunity(opp)
            return opp
        return None

    def _form_goal_from_opportunity(self, opp: Opportunity, t: int) -> Dict:
        """Формирует явную цель из обнаруженной возможности."""
        target = None
        if opp.description.startswith("opened_channel:"):
            target = opp.description.split(":", 1)[1]
        elif opp.description.startswith("high_reward:"):
            target = opp.description.split(":", 1)[1]

        goal = {
            "target": target,
            "reason": opp.description,
            "born_t": t,
            "evidence": list(opp.evidence),
            "status": "active",
        }
        return goal

    def _should_abandon(self, t: int) -> bool:
        if self.current_goal is None:
            return False
        if self.steps_on_goal < 4:
            return False
        target = self.current_goal["target"]
        est = self.log.estimate("w", target, t) if target else None
        if est is not None and est < 0.08:
            return True
        # слишком долго без прогресса
        if self.steps_on_goal > 18:
            return True
        return False

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Возвращает (action, goal_event_or_None)
        goal_event — словарь, который harness превратит в Event(kind=GOAL)
        """
        t = obs["t"]
        reward = obs.get("last_reward")
        opened = obs.get("opened")
        acts = obs.get("available") or []

        if self.last_action is not None and reward is not None:
            self._record(t - 1, self.last_action, reward)
            self._detect_opportunity(self.last_action, reward, opened, t - 1)

        self.t = t
        goal_event = None

        # --- Goal management ---
        if self._should_abandon(t):
            if self.current_goal:
                self.current_goal["status"] = "abandoned"
                self.goal_history.append(self.current_goal)
            self.current_goal = None
            self.steps_on_goal = 0
            goal_event = {"kind": "goal_abandon", "reason": "low_value_or_timeout"}

        # Если нет активной цели — пытаемся сформировать из открытых возможностей
        if self.current_goal is None:
            opps = self.log.open_opportunities()
            if opps:
                # берём самую ценную
                opps.sort(key=lambda o: o.estimated_value, reverse=True)
                chosen = opps[0]
                chosen.status = "pursued"
                self.current_goal = self._form_goal_from_opportunity(chosen, t)
                self.steps_on_goal = 0
                goal_event = {
                    "kind": "goal",
                    "target": self.current_goal["target"],
                    "reason": self.current_goal["reason"],
                    "born_t": t,
                }

        # --- Action selection ---
        action = None
        if self.current_goal and self.current_goal.get("target") in acts:
            # преследуем цель
            action = self.current_goal["target"]
            self.steps_on_goal += 1
        else:
            # исследование: предпочитаем ещё не пробованные
            untried = [a for a in acts if a not in self.explored]
            if untried and self.rng.random() < 0.55:
                action = self.rng.choice(untried)
            elif acts:
                # лёгкая эксплуатация
                best, best_v = None, -1e9
                for a in acts:
                    est = self.log.estimate("w", a, t)
                    v = est if est is not None else 0.0
                    if v > best_v:
                        best_v, best = v, a
                action = best if best is not None else self.rng.choice(acts)
            self.steps_on_goal = 0

        if action:
            self.explored.add(action)
        self.last_action = action
        return action, goal_event


class GreedyExplorer:
    """v0.5.1: КОНТРОЛЬ БЕЗ ЦЕЛЕЙ. Те же сенсоры и тот же опыт, что у GoalAgent,
    но без goal-событий: сначала непробованное, иначе лучшее по оценке."""
    def __init__(self, seed: int):
        self.log = ExperienceLog(half_life=55.0)
        self.rng = random.Random(seed + 29)
        self.last_action: Optional[str] = None
        self.tried: set = set()

    def step(self, obs: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
        t, reward, acts = obs["t"], obs.get("last_reward"), obs.get("available") or []
        if self.last_action is not None and reward is not None:
            self.log.add(Record(t - 1, "w", self.last_action, reward, Source.PID1_INTERNAL))
        if not acts:
            return None, None
        untried = [a for a in acts if a not in self.tried]
        if untried and self.rng.random() < 0.55:
            action = self.rng.choice(untried)
        else:
            def val(a):
                e = self.log.estimate("w", a, t)
                return e if e is not None else 0.0
            action = max(acts, key=val)
        self.tried.add(action)
        self.last_action = action
        return action, None
