from __future__ import annotations

import time

from ...models import Instance, Solution
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..route_constraints import ensure_positive_route_lengths
from .tabu_search import local_clear, tabu_search


class TabuSearchAlgorithm(SolverAlgorithm):
    name = "tabu_search"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        max_iterations = max(1, int(max(0.01, self.config.time_limit) * 200))
        routes, _, iterations_done = tabu_search(
            instance.n,
            instance.k,
            instance.distance,
            max_inter=max_iterations,
            deadline=start + max(0.0, self.config.time_limit),
        )
        if self.config.use_local_search:
            routes = local_clear(
                routes,
                instance.distance,
            )

        solution = Solution(routes)
        solution = ensure_positive_route_lengths(solution, instance)
        solution.assert_feasible(instance)
        runtime = time.perf_counter() - start
        return AlgorithmResult(
            best=solution,
            algorithm=self.name,
            runtime=runtime,
            iterations=iterations_done,
            best_objective=solution.evaluate(instance).as_tuple(),
            stats={"source": "tabu_search"},
        )
