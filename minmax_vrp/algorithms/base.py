from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Distance, Instance, Solution


@dataclass
class AlgorithmConfig:
    time_limit: float = 10.0
    seed: int = 99
    use_local_search: bool = False

    q_min_ratio: float = 0.02
    q_max_ratio: float = 0.10

    initial_temperature: float = 300.0
    cooling_rate: float = 0.999

    reward_global_best: float = 10.0
    reward_current_improved: float = 5.0
    reward_accepted: float = 2.0
    reward_rejected: float = 0.0


@dataclass
class AlgorithmResult:
    best: Solution
    algorithm: str
    runtime: float
    iterations: int = 1
    best_objective: tuple[Distance, Distance, Distance] = (0.0, 0.0, 0.0)
    stats: dict[str, object] = field(default_factory=dict)


class SolverAlgorithm:
    name = "base"

    def solve(self, instance: Instance) -> AlgorithmResult:
        raise NotImplementedError
