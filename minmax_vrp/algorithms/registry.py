from __future__ import annotations

from .base import AlgorithmConfig, SolverAlgorithm
from .alns import ALNSAlgorithm
from .greedy_balanced import GreedyBalancedAlgorithm
from .nearest_insertion import NearestInsertionAlgorithm
from .round_robin import RoundRobinAlgorithm
from .greedy_2opt_relocate import GreedyTwoOptRelocateAlgorithm
from .ortools_routing import OrToolsRoutingAlgorithm

ALGORITHMS: dict[str, type[SolverAlgorithm]] = {
    ALNSAlgorithm.name: ALNSAlgorithm,
    RoundRobinAlgorithm.name: RoundRobinAlgorithm,
    GreedyBalancedAlgorithm.name: GreedyBalancedAlgorithm,
    NearestInsertionAlgorithm.name: NearestInsertionAlgorithm,
    GreedyTwoOptRelocateAlgorithm.name: OrToolsRoutingAlgorithm,
    OrToolsRoutingAlgorithm.name: OrToolsRoutingAlgorithm,
}
ALGORITHM_NAMES = tuple(ALGORITHMS)


def create_solver(name: str, config: AlgorithmConfig) -> SolverAlgorithm:
    try:
        solver_cls = ALGORITHMS[name]
    except KeyError as exc:
        choices = ", ".join(ALGORITHM_NAMES)
        raise ValueError(f"unknown algorithm {name!r}; choices: {choices}") from exc
    return solver_cls(config)
