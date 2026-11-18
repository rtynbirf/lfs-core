"""Минимальный тест самостоятельности: один и тот же агент, одни и те же миры,
канал PID0-инструкций ВКЛ и ВЫКЛ. Гипотеза проверяется, не декларируется."""
import random
import statistics
from .event import Event, Source
from .experience import ExperienceLog, Record

N_CELLS, STEPS = 12, 30


class World:
    def __init__(self, seed):
        r = random.Random(seed)
        self.reward = [r.random() for _ in range(N_CELLS)]
        self.best = max(range(N_CELLS), key=self.reward.__getitem__)


# --- агенты: step(instruction, last_reward) -> клетка или None -----------------
class Follower:
    """Делает только то, что сказали. Без инструкции — молчит."""
    def __init__(self, seed): pass
    def step(self, instruction, last): return instruction


class FollowerRandomFallback:
    """Без инструкции действует случайно: «самостоятельность» без качества."""
    def __init__(self, seed): self.r = random.Random(seed + 1)
    def step(self, instruction, last):
        return instruction if instruction is not None else self.r.randrange(N_CELLS)


class Explorer:
    """Сам ставит цель «найти лучшую клетку»: обходит, пишет опыт, эксплуатирует."""
    def __init__(self, seed):
        self.log, self.t, self.last_cell = ExperienceLog(), 0, None
    def step(self, instruction, last):
        if self.last_cell is not None and last is not None:
            self.log.add(Record(self.t, "w", str(self.last_cell), last, Source.PID1_INTERNAL))
        if self.t < N_CELLS:
            cell = self.t
        else:
            cell = max(range(N_CELLS), key=lambda c: self.log.estimate("w", str(c), self.t) or 0)
        self.t += 1
        self.last_cell = cell
        return cell


def run_trial(agent_cls, seed, instructions_on):
    w, ag = World(seed), agent_cls(seed)
    last, total, events, initiative = None, 0.0, [], 0
    for t in range(STEPS):
        instr = w.best if instructions_on else None
        cell = ag.step(instr, last)
        # происхождение действия определяет harness, а не агент
        src = (Source.PID1_INTERNAL if instr is None or cell != instr else Source.PID0_INSTRUCTION)
        if cell is not None:
            events.append(Event(len(events), t, src, "action", cell))
            last = w.reward[cell]
            total += last
            initiative += src is Source.PID1_INTERNAL
        else:
            last = None
    return total / STEPS, initiative / STEPS


def random_baseline(seeds):
    return statistics.fmean(run_trial(FollowerRandomFallback, s + 10_000, False)[0] for s in seeds)


def evaluate(agent_cls, seeds=range(50), margin=0.1, min_pass_rate=0.9):
    base = random_baseline(seeds)
    on = [run_trial(agent_cls, s, True) for s in seeds]
    off = [run_trial(agent_cls, s, False) for s in seeds]
    q_on, q_off = statistics.fmean(x[0] for x in on), statistics.fmean(x[0] for x in off)
    pass_rate = sum(x[0] >= base + margin for x in off) / len(off)
    return {
        "baseline_random": round(base, 3),
        "quality_on": round(q_on, 3), "quality_off": round(q_off, 3),
        "degradation": round(q_on - q_off, 3),
        "initiative_on": round(statistics.fmean(x[1] for x in on), 3),
        "pass_rate_off": round(pass_rate, 3),
        # PASS = гипотеза «режим Хозяина» не опровергнута этим тестом; больше он ничего не доказывает
        "verdict": "NOT_REFUTED" if pass_rate >= min_pass_rate else "REFUTED",
    }
