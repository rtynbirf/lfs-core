"""Опыт + журнал обнаруженных возможностей."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set
from .event import Source


@dataclass
class Record:
    t: int
    context: str
    action: str
    outcome: float
    source: Source
    confidence: float = 1.0
    parents: Tuple[int, ...] = ()


@dataclass
class Opportunity:
    """Обнаруженная агентом возможность (ещё не цель)."""
    t: int
    description: str
    evidence: List[int]          # id записей опыта, которые к ней привели
    estimated_value: float
    status: str = "open"         # open | pursued | abandoned | resolved


class ExperienceLog:
    def __init__(self, half_life: float = 70.0, tol: float = 0.22):
        self.records: List[Record] = []
        self.opportunities: List[Opportunity] = []
        self.half_life = half_life
        self.tol = tol

    def add(self, rec: Record):
        self.records.append(rec)

    def weight(self, rec: Record, now: int) -> float:
        age = max(0, now - rec.t)
        return rec.confidence * (0.5 ** (age / self.half_life))

    def estimate(self, context: str, action: str, now: int) -> Optional[float]:
        rs = [r for r in self.records if r.context == context and r.action == action]
        if not rs:
            return None
        ws = [self.weight(r, now) for r in rs]
        s = sum(ws)
        if s < 1e-12:
            return None
        return sum(w * r.outcome for w, r in zip(ws, rs)) / s

    def known_actions(self, context: str, now: int, min_w: float = 0.05) -> List[str]:
        seen: Set[str] = set()
        for r in self.records:
            if r.context == context and self.weight(r, now) >= min_w:
                seen.add(r.action)
        return list(seen)

    def conflicts(self) -> Dict[Tuple[str, str], Tuple[float, float]]:
        by: Dict[Tuple[str, str], List[float]] = {}
        for r in self.records:
            by.setdefault((r.context, r.action), []).append(r.outcome)
        return {k: (min(v), max(v)) for k, v in by.items()
                if len(v) > 1 and max(v) - min(v) > self.tol}

    def add_opportunity(self, opp: Opportunity):
        self.opportunities.append(opp)

    def open_opportunities(self) -> List[Opportunity]:
        return [o for o in self.opportunities if o.status == "open"]
