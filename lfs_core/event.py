"""Определение события. Единственный источник правды о происхождении."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Source(str, Enum):
    PID0_ENV = "pid0_env"                # стихийное условие среды (не от агентов)
    PID0_INSTRUCTION = "pid0_instruction"  # внешняя инструкция/цель извне
    PID1_INTERNAL = "pid1_internal"      # цель/действие, порождённое самим агентом
    UNKNOWN = "unknown"                  # происхождение не установлено -> не считается внутренним


@dataclass(frozen=True)
class Event:
    id: int
    t: float
    source: Source
    kind: str                 # "observation" | "goal" | "action" | "outcome"
    payload: Any = None
    confidence: float = 1.0   # 0..1, уверенность в самой записи
    parents: tuple = field(default_factory=tuple)  # id событий-причин


def is_internal(e: Event) -> bool:
    """Внутренним считается только то, что harness пометил PID1_INTERNAL.
    Самоотчёт агента о происхождении НЕ принимается."""
    return e.source is Source.PID1_INTERNAL
