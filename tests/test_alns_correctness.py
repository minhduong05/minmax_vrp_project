import random

import pytest

from minmax_vrp.algorithms.alns.acceptance import SimulatedAnnealingAcceptance
from minmax_vrp.algorithms.alns.solver import ALNSConfig, ALNSSolver
from minmax_vrp.algorithms.route_constraints import has_positive_route_lengths
from minmax_vrp.models import Instance, Solution, better


def test_acceptance_always_accepts_lexicographic_improvement():
    distance = [[0.0 for _ in range(4)] for _ in range(4)]
    distance[0][1] = 10.0
    distance[0][2] = 0.001
    distance[2][1] = 9.998998
    distance[0][3] = 9.999998
    instance = Instance(n=3, k=2, distance=distance)
    current = Solution([[0, 1], [0, 2, 3]])
    candidate = Solution([[0, 2, 1], [0, 3]])
    acceptance = SimulatedAnnealingAcceptance(initial_temperature=0.0, cooling_rate=1.0)

    assert current.is_feasible(instance)
    assert candidate.is_feasible(instance)
    assert better(candidate, current, instance)
    assert acceptance.scalar_value(candidate, instance) > acceptance.scalar_value(
        current, instance
    )
    assert acceptance.accept(current, candidate, instance, random.Random(0))


def test_better_uses_sorted_route_lengths_before_total_distance():
    distance = [
        [0.0, 10.0, 5.0, 8.0, 4.0],
        [10.0, 0.0, 0.0, 0.0, 0.0],
        [5.0, 0.0, 0.0, 0.0, 0.0],
        [8.0, 0.0, 0.0, 0.0, 0.0],
        [4.0, 0.0, 0.0, 0.0, 0.0],
    ]
    instance = Instance(n=4, k=2, distance=distance)
    lower_total_worse_balance = Solution([[0, 1, 3], [0, 2, 4]])
    higher_total_better_balance = Solution([[0, 1, 2], [0, 3, 4]])

    assert lower_total_worse_balance.is_feasible(instance)
    assert higher_total_better_balance.is_feasible(instance)
    assert lower_total_worse_balance.evaluate(instance).as_tuple() == ((10.0, 5.0), 15.0)
    assert higher_total_better_balance.evaluate(instance).as_tuple() == ((10.0, 8.0), 18.0)
    assert better(lower_total_worse_balance, higher_total_better_balance, instance)


def test_alns_requires_positive_route_lengths_by_default():
    distance = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 3.0],
        [2.0, 3.0, 0.0],
    ]
    instance = Instance(n=2, k=3, distance=distance)
    solver = ALNSSolver(ALNSConfig(time_limit=0.0, seed=1))

    with pytest.raises(ValueError, match="positive-length route"):
        solver.solve(instance)


def test_alns_allows_empty_routes_only_when_explicitly_configured():
    distance = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 3.0],
        [2.0, 3.0, 0.0],
    ]
    instance = Instance(n=2, k=3, distance=distance)
    result = ALNSSolver(
        ALNSConfig(time_limit=0.0, seed=1, require_positive_route_lengths=False)
    ).solve(instance)

    assert result.best.is_feasible(instance)
    assert not has_positive_route_lengths(result.best, instance)
    assert result.best_objective == result.best.evaluate(instance).as_tuple()


def test_alns_keeps_every_route_positive_on_normal_instance():
    distance = [
        [0.0, 1.0, 2.0, 3.0],
        [1.0, 0.0, 1.5, 2.5],
        [2.0, 1.5, 0.0, 1.0],
        [3.0, 2.5, 1.0, 0.0],
    ]
    instance = Instance(n=3, k=3, distance=distance)
    result = ALNSSolver(ALNSConfig(time_limit=0.01, seed=3)).solve(instance)

    assert result.best.is_feasible(instance)
    assert has_positive_route_lengths(result.best, instance)


def test_alns_rejects_positive_route_requirement_when_impossible():
    distance = [
        [0.0, 1.0, 2.0],
        [1.0, 0.0, 3.0],
        [2.0, 3.0, 0.0],
    ]
    instance = Instance(n=2, k=3, distance=distance)
    solver = ALNSSolver(
        ALNSConfig(time_limit=0.0, seed=1, require_positive_route_lengths=True)
    )

    with pytest.raises(ValueError, match="positive-length route"):
        solver.solve(instance)


def test_alns_config_rejects_invalid_segment_length():
    with pytest.raises(ValueError, match="segment_length must be positive"):
        ALNSConfig(segment_length=0)


def test_alns_config_rejects_inverted_destroy_range():
    with pytest.raises(ValueError, match="q_max_ratio"):
        ALNSConfig(q_min_ratio=0.2, q_max_ratio=0.1)


def test_alns_config_uses_tuned_size_defaults():
    expected = [
        (100, 0.03, 0.10, 0.999, 50),
        (300, 0.01, 0.05, 0.999, 50),
        (500, 0.005, 0.03, 0.9995, 100),
        (1000, 0.003, 0.02, 0.999, 100),
    ]

    for n, q_min_ratio, q_max_ratio, cooling_rate, segment_length in expected:
        config = ALNSConfig().with_size_defaults(n)
        assert config.q_min_ratio == q_min_ratio
        assert config.q_max_ratio == q_max_ratio
        assert config.cooling_rate == cooling_rate
        assert config.reaction == 0.10
        assert config.segment_length == segment_length
