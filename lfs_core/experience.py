"""Опыт: append-only, конфликты, устаревание, оценка без выдумок."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from .event import Source


@dataclass
class Record:
    t: float
    context: str
    action: str
    outcome: float
    source: Source
    confidence: float = 1.0
    parents: Tuple[int, ...] = ()


class ExperienceLog:
    def __init__(self, half_life: float = 80.0, tol: float = 0.25):
        self.records: List[Record] = []
        self.half_life = half_life
        self.tol = tol

    def add(self, rec: Record):
        self.records.append(rec)

    def weight(self, rec: Record, now: float) -> float:
        age = max(0.0, now - rec.t)
        return rec.confidence * (0.5 ** (age / self.half_life))

    def conflicts(self) -> Dict[Tuple[str, str], Tuple[float, float]]:
        by: Dict[Tuple[str, str], List[float]] = {}
        for r in self.records:
            by.setdefault((r.context, r.action), []).append(r.outcome)
        return {k: (min(v), max(v)) for k, v in by.items()
                if len(v) > 1 and max(v) - min(v) > self.tol}

    def estimate(self, context: str, action: str, now: float) -> Optional[float]:
        rs = [r for r in self.records if r.context == context and r.action == action]
        if not rs:
            return None
        ws = [self.weight(r, now) for r in rs]
        s = sum(ws)
        if s <= 1e-12:
            return None
        return sum(w * r.outcome for w, r in zip(ws, rs)) / s

    def known_actions(self, context: str, now: float, min_w: float = 0.05) -> List[str]:
        seen = {}
        for r in self.records:
            if r.context == context and self.weight(r, now) >= min_w:
                seen[r.action] = True
        return list(seen.keys())

    def stale(self, now: float, min_weight: float = 0.08) -> List[Record]:
        return [r for r in self.records if self.weight(r, now) < min_weight]
