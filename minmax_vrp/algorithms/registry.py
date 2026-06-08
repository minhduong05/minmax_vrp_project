from __future__ import annotations

from .alns import ALNSAlgorithm
from .base import AlgorithmConfig, SolverAlgorithm
from .tabu_search import TabuSearchAlgorithm
from .vns import VNSAlgorithm


ALGORITHMS: dict[str, type[SolverAlgorithm]] = {
    ALNSAlgorithm.name: ALNSAlgorithm,
    VNSAlgorithm.name: VNSAlgorithm,
    TabuSearchAlgorithm.name: TabuSearchAlgorithm,
}
ALGORITHM_NAMES = tuple(ALGORITHMS)


def create_solver(name: str, config: AlgorithmConfig) -> SolverAlgorithm:
    try:
        solver_cls = ALGORITHMS[name]
    except KeyError as exc:
        choices = ", ".join(ALGORITHM_NAMES)
        raise ValueError(f"unknown algorithm {name!r}; choices: {choices}") from exc
    return solver_cls(config)
