"""Событие. Происхождение цели и действия определяет ТОЛЬКО harness."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple, Optional


class Source(str, Enum):
    PID0_ENV = "pid0_env"
    PID0_INSTRUCTION = "pid0_instruction"
    PID1_INTERNAL = "pid1_internal"
    UNKNOWN = "unknown"


class Kind(str, Enum):
    OBSERVATION = "observation"
    GOAL = "goal"                # цель, порождённая системой
    ACTION = "action"
    OUTCOME = "outcome"
    LAW_CHANGE = "law_change"
    GOAL_ABANDON = "goal_abandon"
    GOAL_REVISE = "goal_revise"


@dataclass(frozen=True)
class Event:
    id: int
    t: int
    source: Source
    kind: Kind
    payload: Any = None
    confidence: float = 1.0
    parents: Tuple[int, ...] = field(default_factory=tuple)

    def is_internal_goal(self) -> bool:
        return self.kind is Kind.GOAL and self.source is Source.PID1_INTERNAL
