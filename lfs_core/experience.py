"""Протокол записи опыта: источник, уверенность, противоречия, устаревание."""
from dataclasses import dataclass
from typing import List
from .event import Source


@dataclass
class Record:
    t: float
    context: str
    action: str
    outcome: float
    source: Source
    confidence: float = 1.0


class ExperienceLog:
    def __init__(self, half_life: float = 100.0, tol: float = 0.2):
        self.records: List[Record] = []
        self.half_life = half_life
        self.tol = tol

    def add(self, rec: Record):
        self.records.append(rec)          # append-only: ошибки и разрывы тоже пишутся

    def weight(self, rec: Record, now: float) -> float:
        return rec.confidence * 0.5 ** (max(0.0, now - rec.t) / self.half_life)

    def conflicts(self):
        """Пары (context, action), где наблюдения расходятся больше tol."""
        by = {}
        for r in self.records:
            by.setdefault((r.context, r.action), []).append(r.outcome)
        return {k: (min(v), max(v)) for k, v in by.items()
                if len(v) > 1 and max(v) - min(v) > self.tol}

    def estimate(self, context: str, action: str, now: float):
        """Взвешенная оценка исхода; None если опыта нет (не выдумываем)."""
        rs = [r for r in self.records if r.context == context and r.action == action]
        ws = [self.weight(r, now) for r in rs]
        if not rs or sum(ws) == 0:
            return None
        return sum(w * r.outcome for w, r in zip(ws, rs)) / sum(ws)

    def stale(self, now: float, min_weight: float = 0.1):
        return [r for r in self.records if self.weight(r, now) < min_weight]
