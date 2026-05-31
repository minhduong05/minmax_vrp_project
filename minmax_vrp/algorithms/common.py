from __future__ import annotations

import random

from ..models import Instance, Solution
from .alns.local_search import improve
from .base import AlgorithmConfig, AlgorithmResult


def maybe_improve(
    solution: Solution,
    instance: Instance,
    config: AlgorithmConfig,
    start_time: float,
) -> Solution:
    if not config.use_local_search:
        return solution
    rng = random.Random(config.seed)
    deadline = start_time + max(0.0, config.time_limit)
    return improve(
        solution,
        instance,
        rng,
        max_rounds=config.local_search_rounds,
        deadline=deadline,
    )


def result_from_solution(
    name: str,
    solution: Solution,
    instance: Instance,
    runtime: float,
) -> AlgorithmResult:
    solution.assert_feasible(instance)
    return AlgorithmResult(
        best=solution,
        algorithm=name,
        runtime=runtime,
        iterations=1,
        best_objective=solution.evaluate(instance).as_tuple(),
    )
