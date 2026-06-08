from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class RunMetric:
    seed: int
    best_max: float
    best_total: float
    balance: float
    iterations: int


def summarize(metrics: list[RunMetric]) -> dict[str, float]:
    if not metrics:
        return {}
    max_values = [m.best_max for m in metrics]
    totals = [m.best_total for m in metrics]
    return {
        "runs": float(len(metrics)),
        "best_max_min": min(max_values),
        "best_max_mean": statistics.mean(max_values),
        "best_max_std": statistics.pstdev(max_values) if len(max_values) > 1 else 0.0,
        "total_mean": statistics.mean(totals),
    }

