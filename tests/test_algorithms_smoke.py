import pytest

from minmax_vrp.algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver
from minmax_vrp.models import Instance


def small_instance() -> Instance:
    size = 6
    distance = []
    for i in range(size):
        row = []
        for j in range(size):
            row.append(0 if i == j else abs(i - j) + 1)
        distance.append(row)
    return Instance(n=5, k=2, distance=distance)


@pytest.mark.parametrize("algorithm", ALGORITHM_NAMES)
def test_registered_algorithm_returns_feasible_solution(algorithm):
    instance = small_instance()
    config = AlgorithmConfig(time_limit=0.01, seed=7)

    result = create_solver(algorithm, config).solve(instance)

    assert result.algorithm == algorithm
    assert result.best.is_feasible(instance)
    assert result.best_objective == result.best.evaluate(instance).as_tuple()
    assert result.runtime >= 0
