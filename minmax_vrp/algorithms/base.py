from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Instance, Solution


@dataclass
class AlgorithmConfig:
    time_limit: float = 10.0
    seed: int = 99
    include_return_to_depot: bool = False
    use_local_search: bool = False
    local_search_rounds: int = 2

    q_min_ratio: float = 0.05
    q_max_ratio: float = 0.20
    q_min_cap: int = 6
    q_max_cap: int = 24


@dataclass
class AlgorithmResult:
    best: Solution
    algorithm: str
    runtime: float
    iterations: int = 1
    best_objective: tuple[int, int, int] = (0, 0, 0)
    stats: dict[str, object] = field(default_factory=dict)


class SolverAlgorithm:
    name = "base"

    def solve(self, instance: Instance) -> AlgorithmResult:
        raise NotImplementedError
