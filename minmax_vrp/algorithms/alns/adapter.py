from __future__ import annotations

from ...models import Instance
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from .solver import ALNSConfig, ALNSSolver


class ALNSAlgorithm(SolverAlgorithm):
    name = "alns"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        solver = ALNSSolver(
            ALNSConfig(
                time_limit=self.config.time_limit,
                seed=self.config.seed,
                q_min_ratio=self.config.q_min_ratio,
                q_max_ratio=self.config.q_max_ratio,
                q_min_cap=self.config.q_min_cap,
                q_max_cap=self.config.q_max_cap,
                use_local_search=self.config.use_local_search,
                local_search_rounds=self.config.local_search_rounds,
                include_return_to_depot=self.config.include_return_to_depot,
            )
        )
        result = solver.solve(instance)
        return AlgorithmResult(
            best=result.best,
            algorithm=self.name,
            runtime=result.runtime,
            iterations=result.iterations,
            best_objective=result.best_objective,
            stats={
                "destroy_weights": result.destroy_weights,
                "repair_weights": result.repair_weights,
            },
        )
