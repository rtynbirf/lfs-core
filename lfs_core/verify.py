"""Проверка модели: должна бить тривиальный baseline на отложенных данных."""
import statistics
from typing import Callable, List, Tuple, Dict, Any

Point = Tuple[str, str, float]  # context, action, outcome


def _mae(pred: Callable, pts: List[Point], default: float) -> float:
    errs = []
    for c, a, y in pts:
        p = pred(c, a)
        errs.append(abs((default if p is None else p) - y))
    return sum(errs) / max(1, len(errs))


def verify_model(fit: Callable[[List[Point]], Callable],
                 data: List[Point],
                 folds: int = 5,
                 ratio: float = 0.85,
                 min_pass_rate: float = 0.75) -> Dict[str, Any]:
    n = len(data)
    if n < folds * 3:
        return {"verdict": "INSUFFICIENT_DATA", "n": n}
    results = []
    for k in range(folds):
        test = data[k::folds]
        train = [p for i, p in enumerate(data) if i % folds != k]
        mean = statistics.fmean(y for _, _, y in train) if train else 0.5
        model = fit(train)
        m = _mae(model, test, mean)
        b = _mae(lambda c, a: mean, test, mean)
        results.append((m, b))
    passes = sum(1 for m, b in results if m <= ratio * b)
    rate = passes / folds
    return {
        "verdict": "PASS" if rate >= min_pass_rate else "FAIL",
        "pass_rate": round(rate, 3),
        "model_mae": round(statistics.fmean(m for m, _ in results), 4),
        "baseline_mae": round(statistics.fmean(b for _, b in results), 4),
    }
