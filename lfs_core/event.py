"""Событие. Происхождение ставит ТОЛЬКО harness. Самоотчёт агента игнорируется."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Tuple


class Source(str, Enum):
    PID0_ENV = "pid0_env"                  # стихийное / структурное условие среды
    PID0_INSTRUCTION = "pid0_instruction"  # внешняя цель/инструкция
    PID1_INTERNAL = "pid1_internal"        # порождено самим агентом
    UNKNOWN = "unknown"                    # происхождение не установлено


@dataclass(frozen=True)
class Event:
    id: int
    t: float
    source: Source
    kind: str                 # observation | goal | action | outcome | law_change
    payload: Any = None
    confidence: float = 1.0
    parents: Tuple[int, ...] = field(default_factory=tuple)

    def is_internal(self) -> bool:
        return self.source is Source.PID1_INTERNAL
