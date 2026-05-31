from __future__ import annotations

import time

from ...models import Instance
from ..alns.construction import build_greedy_balanced
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..common import maybe_improve, result_from_solution


class GreedyBalancedAlgorithm(SolverAlgorithm):
    name = "greedy_balanced"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        solution = build_greedy_balanced(
            instance,
            include_return_to_depot=self.config.include_return_to_depot,
            seed=self.config.seed,
        )
        solution = maybe_improve(solution, instance, self.config, start)
        return result_from_solution(self.name, solution, instance, time.perf_counter() - start)
