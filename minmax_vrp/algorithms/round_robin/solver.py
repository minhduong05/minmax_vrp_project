from __future__ import annotations

import time

from ...models import Instance
from ..alns.construction import build_round_robin
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..common import maybe_improve, result_from_solution


class RoundRobinAlgorithm(SolverAlgorithm):
    name = "round_robin"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        solution = build_round_robin(instance, self.config.include_return_to_depot)
        solution = maybe_improve(solution, instance, self.config, start)
        return result_from_solution(self.name, solution, instance, time.perf_counter() - start)
