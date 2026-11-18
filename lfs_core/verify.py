"""Протокол проверки модели. «Работает» != «кажется, что работает».
Модель PASS, только если бьёт тривиальный baseline на отложенных данных
в доле фолдов не меньше min_pass_rate."""
import statistics
from typing import Callable, List, Tuple

Point = Tuple[str, str, float]  # (context, action, outcome)


def _mae(pred: Callable, pts: List[Point], default: float) -> float:
    errs = []
    for c, a, y in pts:
        p = pred(c, a)
        errs.append(abs((default if p is None else p) - y))
    return sum(errs) / len(errs)


def verify_model(fit: Callable[[List[Point]], Callable], data: List[Point],
                 folds: int = 5, ratio: float = 0.8, min_pass_rate: float = 0.8):
    """fit(train)->predict(context, action). Baseline = среднее по train."""
    n = len(data)
    if n < folds * 2:
        return {"verdict": "INSUFFICIENT_DATA", "n": n}
    res = []
    for k in range(folds):
        test = data[k::folds]
        train = [p for i, p in enumerate(data) if i % folds != k]
        mean = statistics.fmean(y for _, _, y in train)
        m = _mae(fit(train), test, mean)
        b = _mae(lambda c, a: mean, test, mean)
        res.append((m, b))
    passes = sum(1 for m, b in res if m <= ratio * b)
    rate = passes / folds
    return {"verdict": "PASS" if rate >= min_pass_rate else "FAIL",
            "pass_rate": rate, "model_mae": statistics.fmean(m for m, _ in res),
            "baseline_mae": statistics.fmean(b for _, b in res)}
