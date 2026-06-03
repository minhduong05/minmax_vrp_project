from __future__ import annotations

import random
import time

from ...models import Instance, Solution, better
from ..alns.construction import build_greedy_balanced
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm


class GreedyTwoOptRelocateAlgorithm(SolverAlgorithm):
    name = "greedy_2opt_relocate"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        rng = random.Random(self.config.seed)
        solution = build_greedy_balanced(
            instance,
            include_return_to_depot=self.config.include_return_to_depot,
            seed=self.config.seed,
        )
        solution = _improve_with_relocate_and_two_opt(
            solution,
            instance,
            rng,
            max_rounds=max(1, self.config.local_search_rounds),
            deadline=start + max(0.0, self.config.time_limit),
        )
        solution.assert_feasible(instance)
        runtime = time.perf_counter() - start
        return AlgorithmResult(
            best=solution,
            algorithm=self.name,
            runtime=runtime,
            iterations=1,
            best_objective=solution.evaluate(instance).as_tuple(),
            stats={
                "construction": "greedy_balanced",
                "local_search": "relocate+2opt",
            },
        )


def _improve_with_relocate_and_two_opt(
    solution: Solution,
    instance: Instance,
    rng: random.Random,
    max_rounds: int,
    deadline: float | None,
) -> Solution:
    current = solution.copy()
    for _ in range(max_rounds):
        if _out_of_time(deadline):
            break
        improved = False

        relocate_candidate = _relocate_from_longest(current, instance, rng, deadline)
        if better(relocate_candidate, current, instance):
            current = relocate_candidate
            improved = True

        if _out_of_time(deadline):
            break

        two_opt_candidate = _two_opt_long_routes(current, instance, rng, deadline)
        if better(two_opt_candidate, current, instance):
            current = two_opt_candidate
            improved = True

        if not improved:
            break
    return current


def _relocate_from_longest(
    solution: Solution, instance: Instance, rng: random.Random, deadline: float | None
) -> Solution:
    best = solution.copy()
    lengths = solution.route_lengths(instance)
    if not lengths:
        return best

    longest = _longest_route_index(lengths)
    route = solution.routes[longest]
    positions = list(range(1, len(route)))
    rng.shuffle(positions)
    positions = positions[: min(20, len(positions))]

    for pos in positions:
        if _out_of_time(deadline):
            break
        point = route[pos]
        base = solution.copy()
        base.routes[longest].pop(pos)
        for target_route_idx, target_route in enumerate(base.routes):
            if _out_of_time(deadline):
                break
            for insert_pos in range(1, len(target_route) + 1):
                candidate = base.copy()
                candidate.routes[target_route_idx].insert(insert_pos, point)
                if better(candidate, best, instance):
                    best = candidate
    return best


def _two_opt_long_routes(
    solution: Solution, instance: Instance, rng: random.Random, deadline: float | None
) -> Solution:
    best = solution.copy()
    lengths = solution.route_lengths(instance)
    route_order = list(range(len(lengths)))
    route_order.sort(key=lambda route_idx: lengths[route_idx], reverse=True)
    route_order = route_order[: min(5, len(route_order))]

    for route_idx in route_order:
        if _out_of_time(deadline):
            break
        route = solution.routes[route_idx]
        route_size = len(route)
        if route_size <= 4:
            continue
        max_pairs = min(80, (route_size - 1) * (route_size - 2) // 2)
        pairs: list[tuple[int, int]] = []
        for _ in range(max_pairs):
            left = rng.randint(1, route_size - 2)
            right = rng.randint(left + 1, route_size - 1)
            pairs.append((left, right))
        for left, right in pairs:
            if _out_of_time(deadline):
                break
            candidate = solution.copy()
            candidate.routes[route_idx][left : right + 1] = reversed(
                candidate.routes[route_idx][left : right + 1]
            )
            if better(candidate, best, instance):
                best = candidate
    return best


def _out_of_time(deadline: float | None) -> bool:
    return deadline is not None and time.perf_counter() >= deadline


def _longest_route_index(lengths: list[int]) -> int:
    longest = 0
    for route_idx in range(1, len(lengths)):
        if lengths[route_idx] > lengths[longest]:
            longest = route_idx
    return longest