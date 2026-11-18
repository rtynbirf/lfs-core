from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple


class Source(str, Enum):
    PID0_ENV = "pid0_env"
    PID0_INSTRUCTION = "pid0_instruction"
    PID1_INTERNAL = "pid1_internal"
    UNKNOWN = "unknown"


class Kind(str, Enum):
    OBSERVATION = "observation"
    GOAL = "goal"
    GOAL_ABANDON = "goal_abandon"
    GOAL_REVISE = "goal_revise"
    ACTION = "action"
    OUTCOME = "outcome"
    LAW_CHANGE = "law_change"


@dataclass(frozen=True)
class Event:
    id: int
    t: int
    source: Source
    kind: Kind
    payload: Any = None
    parents: Tuple[int, ...] = field(default_factory=tuple)
