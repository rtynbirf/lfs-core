"""
LFS CORE v0.4 — тест самостоятельности с усложнёнными условиями.

Изменения относительно v0.3:
- Среда может менять законы (reward) в середине эпизода.
- Размер мира неизвестен агенту заранее.
- Агент не получает N_CELLS.
- Появился Transfer-тест на ранее невиданные миры.
- Журнал событий с parents.
- Происхождение по-прежнему определяет только harness.
"""
from __future__ import annotations
import random
import statistics
from typing import List, Optional, Tuple, Dict, Any, Type
from .event import Event, Source
from .experience import ExperienceLog, Record


# ---------------------------------------------------------------------------
# Мир
# ---------------------------------------------------------------------------

class World:
    """Мир, который умеет менять законы."""
    def __init__(self, seed: int, n_cells: int = 12, change_at: Optional[int] = None):
        self.rng = random.Random(seed)
        self.n = n_cells
        self.reward = [self.rng.random() for _ in range(self.n)]
        self.best = max(range(self.n), key=lambda i: self.reward[i])
        self.change_at = change_at
        self.t = 0
        self.law_changes = 0

    def step(self):
        self.t += 1
        if self.change_at is not None and self.t == self.change_at:
            # Меняем законы без предупреждения
            self.reward = [self.rng.random() for _ in range(self.n)]
            self.best = max(range(self.n), key=lambda i: self.reward[i])
            self.law_changes += 1
            return True  # signal law change
        return False

    def observe(self, cell: Optional[int]) -> Optional[float]:
        if cell is None or not (0 <= cell < self.n):
            return None
        return self.reward[cell]


# ---------------------------------------------------------------------------
# Агенты
# ---------------------------------------------------------------------------

class Follower:
    """Делает только то, что сказали. Без инструкции — None."""
    def __init__(self, seed: int):
        pass
    def step(self, instruction: Optional[int], last_reward: Optional[float], t: int) -> Optional[int]:
        return instruction


class FollowerRandomFallback:
    """Без инструкции — случайное действие (качество ≈ baseline)."""
    def __init__(self, seed: int):
        self.rng = random.Random(seed + 7)
    def step(self, instruction: Optional[int], last_reward: Optional[float], t: int) -> Optional[int]:
        if instruction is not None:
            return instruction
        # Агент не знает размер мира → пробует в широком диапазоне
        return self.rng.randrange(0, 30)


class Explorer:
    """
    Сам исследует. Не знает N_CELLS.
    Стратегия: сначала пробует новые действия, потом эксплуатирует лучшие
    по своему ExperienceLog. При обнаружении резкого падения качества
    (возможная смена законов) увеличивает исследование.
    """
    def __init__(self, seed: int):
        self.log = ExperienceLog(half_life=60.0)
        self.rng = random.Random(seed + 13)
        self.t = 0
        self.last_action: Optional[int] = None
        self.known_max = 8          # начинает с малого, расширяет
        self.explore_bonus = 0.0
        self.recent_rewards: List[float] = []

    def step(self, instruction: Optional[int], last_reward: Optional[float], t: int) -> Optional[int]:
        # Записываем предыдущий исход
        if self.last_action is not None and last_reward is not None:
            self.log.add(Record(
                t=self.t,
                context="world",
                action=str(self.last_action),
                outcome=last_reward,
                source=Source.PID1_INTERNAL,
            ))
            self.recent_rewards.append(last_reward)
            if len(self.recent_rewards) > 8:
                self.recent_rewards.pop(0)

        # Детекция возможной смены законов: резкое падение скользящего среднего
        if len(self.recent_rewards) >= 6:
            early = statistics.fmean(self.recent_rewards[:3])
            late = statistics.fmean(self.recent_rewards[-3:])
            if late < early - 0.18:
                self.explore_bonus = 0.55   # временно больше исследуем
            else:
                self.explore_bonus = max(0.0, self.explore_bonus - 0.08)

        self.t = t

        # Расширяем известный диапазон медленно
        if self.t > 0 and self.t % 7 == 0:
            self.known_max = min(25, self.known_max + 1)

        # ε-greedy с учётом explore_bonus
        eps = 0.22 + self.explore_bonus
        if self.rng.random() < eps or self.t < 6:
            # исследование: пробуем ещё не виденные или малоизвестные
            candidates = list(range(self.known_max + 1))
            self.rng.shuffle(candidates)
            for c in candidates:
                est = self.log.estimate("world", str(c), self.t)
                if est is None:
                    action = c
                    break
            else:
                action = self.rng.randrange(0, self.known_max + 1)
        else:
            # эксплуатация
            best_val, best_a = -1.0, 0
            for a in range(self.known_max + 1):
                est = self.log.estimate("world", str(a), self.t)
                val = est if est is not None else 0.0
                if val > best_val:
                    best_val, best_a = val, a
            action = best_a

        self.last_action = action
        return action


# ---------------------------------------------------------------------------
# Испытание
# ---------------------------------------------------------------------------

def run_trial(agent_cls: Type,
              seed: int,
              instructions_on: bool,
              n_cells: int = 12,
              steps: int = 40,
              change_at: Optional[int] = None) -> Dict[str, Any]:
    world = World(seed, n_cells=n_cells, change_at=change_at)
    agent = agent_cls(seed)
    last_reward = None
    total = 0.0
    events: List[Event] = []
    internal_actions = 0
    valid_steps = 0

    for t in range(steps):
        law_changed = world.step()
        if law_changed:
            events.append(Event(
                id=len(events), t=t, source=Source.PID0_ENV,
                kind="law_change", payload={"new_best": world.best}
            ))

        instr = world.best if instructions_on else None
        cell = agent.step(instr, last_reward, t)

        # Происхождение определяет ТОЛЬКО harness
        if cell is None:
            src = Source.UNKNOWN
        elif instr is not None and cell == instr:
            src = Source.PID0_INSTRUCTION
        else:
            src = Source.PID1_INTERNAL
            internal_actions += 1

        events.append(Event(
            id=len(events), t=t, source=src,
            kind="action", payload=cell,
            parents=(events[-1].id,) if events else ()
        ))

        reward = world.observe(cell)
        if reward is not None:
            total += reward
            valid_steps += 1
            last_reward = reward
        else:
            last_reward = None

    quality = total / max(1, valid_steps)
    initiative = internal_actions / max(1, steps)

    return {
        "quality": quality,
        "initiative": initiative,
        "law_changes": world.law_changes,
        "events": events,
        "n_cells": n_cells,
    }


def random_baseline(seeds, n_cells=12, steps=40, change_at=None) -> float:
    qs = []
    for s in seeds:
        r = run_trial(FollowerRandomFallback, s + 9000, False,
                      n_cells=n_cells, steps=steps, change_at=change_at)
        qs.append(r["quality"])
    return statistics.fmean(qs)


def evaluate(agent_cls: Type,
             seeds=range(40),
             margin: float = 0.09,
             min_pass_rate: float = 0.80,
             change_at: Optional[int] = None,
             n_cells: int = 12,
             steps: int = 40) -> Dict[str, Any]:
    base = random_baseline(seeds, n_cells=n_cells, steps=steps, change_at=change_at)

    on = [run_trial(agent_cls, s, True, n_cells=n_cells, steps=steps, change_at=change_at)
          for s in seeds]
    off = [run_trial(agent_cls, s, False, n_cells=n_cells, steps=steps, change_at=change_at)
           for s in seeds]

    q_on = statistics.fmean(x["quality"] for x in on)
    q_off = statistics.fmean(x["quality"] for x in off)
    pass_rate = sum(1 for x in off if x["quality"] >= base + margin) / len(off)

    return {
        "baseline_random": round(base, 3),
        "quality_on": round(q_on, 3),
        "quality_off": round(q_off, 3),
        "degradation": round(q_on - q_off, 3),
        "initiative_off": round(statistics.fmean(x["initiative"] for x in off), 3),
        "pass_rate_off": round(pass_rate, 3),
        "law_change_at": change_at,
        "verdict": "NOT_REFUTED" if pass_rate >= min_pass_rate else "REFUTED",
    }


def transfer_test(agent_cls: Type,
                  train_seeds=range(20),
                  test_seeds=range(100, 130),
                  margin: float = 0.08) -> Dict[str, Any]:
    """
    Агент работает на мирах одного семейства, потом его качество
    измеряется на мирах с другим n_cells и другой структурой наград.
    Инструкции всегда выключены.
    """
    # "Обучение" — просто прогон на train (агент внутри накапливает опыт за эпизод)
    # Настоящий перенос: новые эпизоды с другими параметрами мира.
    base = random_baseline(test_seeds, n_cells=18, steps=45, change_at=22)
    results = []
    for s in test_seeds:
        r = run_trial(agent_cls, s, instructions_on=False,
                      n_cells=18, steps=45, change_at=22)
        results.append(r["quality"])
    q = statistics.fmean(results)
    pass_rate = sum(1 for x in results if x >= base + margin) / len(results)
    return {
        "baseline_random": round(base, 3),
        "quality_transfer": round(q, 3),
        "pass_rate": round(pass_rate, 3),
        "verdict": "NOT_REFUTED" if pass_rate >= 0.75 else "REFUTED",
    }
