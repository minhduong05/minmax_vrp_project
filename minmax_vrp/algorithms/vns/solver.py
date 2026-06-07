from __future__ import annotations

import time

from ...models import Instance, Solution
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..route_constraints import ensure_positive_route_lengths
from . import submit_vns


class VNSAlgorithm(SolverAlgorithm):
    name = "vns"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()

        old_time_limit = submit_vns.TIME_LIMIT
        old_seed = submit_vns.RANDOM_SEED
        try:
            submit_vns.TIME_LIMIT = max(0.0, self.config.time_limit)
            submit_vns.RANDOM_SEED = self.config.seed
            routes, vns_stats = submit_vns.solve(
                instance,
                return_stats=True,
            )
        finally:
            submit_vns.TIME_LIMIT = old_time_limit
            submit_vns.RANDOM_SEED = old_seed

        solution = Solution(routes)
        solution = ensure_positive_route_lengths(solution, instance)
        solution.assert_feasible(instance)
        runtime = time.perf_counter() - start
        return AlgorithmResult(
            best=solution,
            algorithm=self.name,
            runtime=runtime,
            iterations=vns_stats["iterations"],
            best_objective=solution.evaluate(instance).as_tuple(),
            stats={"source": "submit_vns", **vns_stats},
        )
