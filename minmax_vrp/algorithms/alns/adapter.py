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
                initial_temperature=self.config.initial_temperature,
                cooling_rate=self.config.cooling_rate,
                reaction=self.config.reaction,
                segment_length=self.config.segment_length,
                reward_global_best=self.config.reward_global_best,
                reward_current_improved=self.config.reward_current_improved,
                reward_accepted=self.config.reward_accepted,
                reward_rejected=self.config.reward_rejected,
                use_local_search=self.config.use_local_search,
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
                "config": result.config,
            },
        )
