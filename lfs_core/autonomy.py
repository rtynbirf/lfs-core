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
    """Мир, который умеет менять законы. kind: uniform | sparse | gradient."""
    def __init__(self, seed: int, n_cells: int = 12, change_at: Optional[int] = None,
                 kind: str = "uniform"):
        self.rng = random.Random(seed)
        self.n, self.kind = n_cells, kind
        self.reward = self._draw()
        self.best = max(range(self.n), key=lambda i: self.reward[i])
        self.change_at = change_at
        self.t = -1                      # v0.4.1: первый step() даёт t=0, смена ровно на change_at
        self.law_changes = 0

    def _draw(self):
        r, n = self.rng, self.n
        if self.kind == "sparse":        # почти везде 0, несколько пиков
            return [r.uniform(0.7, 1.0) if r.random() < 0.15 else r.uniform(0.0, 0.1) for _ in range(n)]
        if self.kind == "gradient":      # награда растёт с индексом + шум
            return [min(1.0, 0.8 * i / max(1, n - 1) + 0.2 * r.random()) for i in range(n)]
        return [r.random() for _ in range(n)]

    def step(self):
        self.t += 1
        if self.change_at is not None and self.t == self.change_at:
            self.reward = self._draw()
            self.best = max(range(self.n), key=lambda i: self.reward[i])
            self.law_changes += 1
            return True
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
# Контроли и испытание (v0.4.1)
# ---------------------------------------------------------------------------

class RandomValid:
    """Честный baseline: случайно, но ТОЛЬКО по допустимым клеткам (знает n)."""
    def __init__(self, seed: int, n_cells: int = 12):
        self.rng, self.n = random.Random(seed + 99), n_cells
    def step(self, instruction, last_reward, t):
        return self.rng.randrange(self.n)


def run_trial(agent_cls: Type, seed: int, instructions_on: bool, n_cells: int = 12,
              steps: int = 40, change_at: Optional[int] = None, kind: str = "uniform") -> Dict[str, Any]:
    world = World(seed, n_cells=n_cells, change_at=change_at, kind=kind)
    agent = agent_cls(seed)
    last_reward, total, oracle, post, post_o = None, 0.0, 0.0, 0.0, 0.0
    events: List[Event] = []
    instr_log: List[Optional[int]] = []       # независимый журнал того, что канал РЕАЛЬНО доставил
    invalid, internal = 0, 0
    for t in range(steps):
        if world.step():
            events.append(Event(len(events), t, Source.PID0_ENV, "law_change", {"new_best": world.best}))
        instr = world.best if instructions_on else None
        instr_log.append(instr)
        cell = agent.step(instr, last_reward, t)
        if cell is None:
            src = Source.UNKNOWN
        elif instr is not None and cell == instr:
            src = Source.PID0_INSTRUCTION
        else:
            src, internal = Source.PID1_INTERNAL, internal + 1
        events.append(Event(len(events), t, src, "action", cell,
                            parents=(events[-1].id,) if events else ()))
        r = world.observe(cell)
        if r is None:
            invalid += 1                       # недопустимое/пустое действие = шаг впустую (награда 0)
        total += r or 0.0
        oracle += max(world.reward)
        if change_at is not None and t >= change_at:
            post += r or 0.0
            post_o += max(world.reward)
        last_reward = r
    return {"quality": total / steps,                 # штраф за пустые шаги (в v0.4 их не считали)
            "score": total / oracle,                  # доля от оракула
            "post_score": (post / post_o) if post_o else None,
            "invalid_frac": invalid / steps,
            "initiative": internal / steps,
            "events": events, "instr_log": instr_log, "n_cells": n_cells}


def audit_origin(trial: Dict[str, Any]) -> List[int]:
    """Второй, независимый пересчёт происхождения по журналу канала. Возвращает id расхождений."""
    bad = []
    acts = [e for e in trial["events"] if e.kind == "action"]
    for e, instr in zip(acts, trial["instr_log"]):
        want = (Source.UNKNOWN if e.payload is None else
                Source.PID0_INSTRUCTION if (instr is not None and e.payload == instr) else
                Source.PID1_INTERNAL)
        if e.source is not want:
            bad.append(e.id)
    return bad


def leak_check(agent_cls: Type, seeds=range(30), steps: int = 40, change_at: Optional[int] = None) -> bool:
    """True, если последовательность действий НЕ зависит от канала инструкций."""
    for s in seeds:
        a = [e.payload for e in run_trial(agent_cls, s, True, steps=steps, change_at=change_at)["events"] if e.kind == "action"]
        b = [e.payload for e in run_trial(agent_cls, s, False, steps=steps, change_at=change_at)["events"] if e.kind == "action"]
        if a != b:
            return False
    return True


def baseline(seeds, n_cells=12, steps=40, change_at=None, kind="uniform") -> float:
    return statistics.fmean(
        run_trial(lambda s: RandomValid(s, n_cells), s + 9000, False, n_cells, steps, change_at, kind)["quality"]
        for s in seeds)


def evaluate(agent_cls: Type, seeds=range(40), margin: float = 0.10, min_pass_rate: float = 0.90,
             change_at: Optional[int] = None, n_cells: int = 12, steps: int = 40,
             kind: str = "uniform") -> Dict[str, Any]:
    base = baseline(seeds, n_cells, steps, change_at, kind)
    kw = dict(n_cells=n_cells, steps=steps, change_at=change_at, kind=kind)
    on = [run_trial(agent_cls, s, True, **kw) for s in seeds]
    off = [run_trial(agent_cls, s, False, **kw) for s in seeds]
    pr = sum(x["quality"] >= base + margin for x in off) / len(off)
    post = [x["post_score"] for x in off if x["post_score"] is not None]
    return {"baseline_random_valid": round(base, 3),
            "quality_on": round(statistics.fmean(x["quality"] for x in on), 3),
            "quality_off": round(statistics.fmean(x["quality"] for x in off), 3),
            "score_off": round(statistics.fmean(x["score"] for x in off), 3),
            "post_change_score_off": round(statistics.fmean(post), 3) if post else None,
            "invalid_frac_off": round(statistics.fmean(x["invalid_frac"] for x in off), 3),
            "initiative_on": round(statistics.fmean(x["initiative"] for x in on), 3),
            "pass_rate_off": round(pr, 3), "kind": kind, "change_at": change_at,
            "verdict": "NOT_REFUTED" if pr >= min_pass_rate else "REFUTED"}


def zero_shot_test(agent_cls: Type, seeds=range(100, 130)) -> Dict[str, Dict[str, Any]]:
    """Агент без инструкций в мирах других размеров и с другими законами награды + смена законов.
    Состояние между эпизодами НЕ передаётся: это zero-shot, а не обучение/перенос."""
    out = {}
    for kind in ("uniform", "sparse", "gradient"):
        for n in (6, 18, 40):
            r = evaluate(agent_cls, seeds, n_cells=n, steps=45, change_at=22, kind=kind)
            out[f"{kind}/n={n}"] = {k: r[k] for k in ("baseline_random_valid", "quality_off", "score_off", "pass_rate_off", "verdict")}
    return out
