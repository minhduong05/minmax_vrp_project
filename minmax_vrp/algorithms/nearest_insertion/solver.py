from __future__ import annotations

import random
import time

from ...models import Instance, Solution
from ..alns.operators_utils import insertion_delta
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..common import maybe_improve, result_from_solution


class NearestInsertionAlgorithm(SolverAlgorithm):
    name = "nearest_insertion"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        routes = [[0] for _ in range(instance.k)]
        lengths = [0 for _ in range(instance.k)]
        unassigned = set(instance.pickup_points)

        seeds = sorted(unassigned, key=lambda point: instance.distance[0][point])
        for route_idx in range(min(instance.k, len(seeds))):
            point = seeds[route_idx]
            routes[route_idx].append(point)
            unassigned.remove(point)
            lengths[route_idx] = Solution(
                [routes[route_idx]],
                self.config.include_return_to_depot,
            ).route_length(routes[route_idx], instance.distance)

        while unassigned:
            route_idx = min(range(instance.k), key=lambda idx: (lengths[idx], len(routes[idx])))
            anchor = routes[route_idx][-1]
            point = min(unassigned, key=lambda node: instance.distance[anchor][node])
            best_pos = 1
            best_delta = None
            for pos in range(1, len(routes[route_idx]) + 1):
                delta = insertion_delta(
                    routes[route_idx],
                    point,
                    pos,
                    instance,
                    self.config.include_return_to_depot,
                )
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_pos = pos
            routes[route_idx].insert(best_pos, point)
            lengths[route_idx] += best_delta or 0
            unassigned.remove(point)

        solution = Solution(routes, self.config.include_return_to_depot)
        solution = maybe_improve(solution, instance, self.config, start)
        return result_from_solution(self.name, solution, instance, time.perf_counter() - start)
