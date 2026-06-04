from __future__ import annotations

from .base import AlgorithmConfig, SolverAlgorithm


def _available_algorithm_classes() -> list[type[SolverAlgorithm]]:
    classes: list[type[SolverAlgorithm]] = []

    try:
        from .alns import ALNSAlgorithm

        classes.append(ALNSAlgorithm)
    except ModuleNotFoundError:
        pass

    try:
        from .round_robin import RoundRobinAlgorithm

        classes.append(RoundRobinAlgorithm)
    except ModuleNotFoundError:
        pass

    try:
        from .greedy_balanced import GreedyBalancedAlgorithm

        classes.append(GreedyBalancedAlgorithm)
    except ModuleNotFoundError:
        pass

    try:
        from .nearest_insertion import NearestInsertionAlgorithm

        classes.append(NearestInsertionAlgorithm)
    except ModuleNotFoundError:
        pass

    try:
        from .greedy_2opt_relocate import GreedyTwoOptRelocateAlgorithm

        classes.append(GreedyTwoOptRelocateAlgorithm)
    except ModuleNotFoundError:
        pass

    try:
        from .ortools_routing import OrToolsRoutingAlgorithm

        classes.append(OrToolsRoutingAlgorithm)
    except ModuleNotFoundError:
        pass

    return classes


ALGORITHMS: dict[str, type[SolverAlgorithm]] = {
    algorithm.name: algorithm for algorithm in _available_algorithm_classes()
}
ALGORITHM_NAMES = tuple(ALGORITHMS)


def create_solver(name: str, config: AlgorithmConfig) -> SolverAlgorithm:
    try:
        solver_cls = ALGORITHMS[name]
    except KeyError as exc:
        choices = ", ".join(ALGORITHM_NAMES)
        raise ValueError(f"unknown algorithm {name!r}; choices: {choices}") from exc
    return solver_cls(config)
