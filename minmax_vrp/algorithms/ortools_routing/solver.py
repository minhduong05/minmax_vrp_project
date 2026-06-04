from __future__ import annotations

import time

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from ...models import Distance, Instance, Solution
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..greedy_balanced import GreedyBalancedAlgorithm


class OrToolsRoutingAlgorithm(SolverAlgorithm):
    name = "ortools_routing"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        solution, stats = _solve_with_ortools(instance, self.config)
        if solution is None:
            solution = _fallback_solution(instance, self.config)
            stats["fallback_used"] = True
        solution.assert_feasible(instance)
        runtime = time.perf_counter() - start
        return AlgorithmResult(
            best=solution,
            algorithm=self.name,
            runtime=runtime,
            iterations=1,
            best_objective=solution.evaluate(instance).as_tuple(),
            stats=stats,
        )


def _solve_with_ortools(
    instance: Instance, config: AlgorithmConfig
) -> tuple[Solution | None, dict[str, object]]:
    manager = pywrapcp.RoutingIndexManager(instance.n + 1, instance.k, 0)
    routing = pywrapcp.RoutingModel(manager)

    distance_scale = 1000
    max_distance = 0
    for row in instance.distance:
        row_max = max(_scaled_distance(value, distance_scale) for value in row)
        if row_max > max_distance:
            max_distance = row_max

    def transit_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        if to_node == 0:
            if config.include_return_to_depot and from_node != 0:
                return _scaled_distance(instance.distance[from_node][0], distance_scale)
            return 0
        return _scaled_distance(instance.distance[from_node][to_node], distance_scale)

    transit_callback_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    horizon = max(1, instance.n * max_distance)
    routing.AddDimension(
        transit_callback_index,
        0,
        horizon,
        True,
        "Distance",
    )
    distance_dimension = routing.GetDimensionOrDie("Distance")
    distance_dimension.SetGlobalSpanCostCoefficient(horizon + 1)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.log_search = False
    _set_time_limit(search_parameters, config.time_limit)

    assignment = routing.SolveWithParameters(search_parameters)
    if assignment is None:
        return None, {
            "solver": "ortools",
            "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
            "metaheuristic": "GUIDED_LOCAL_SEARCH",
            "fallback_used": False,
        }

    routes = []
    route_lengths: list[Distance] = []
    for vehicle_idx in range(instance.k):
        index = routing.Start(vehicle_idx)
        route = [0]
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                route.append(node)
            index = assignment.Value(routing.NextVar(index))
        routes.append(route)
        route_lengths.append(
            _route_length(route, instance.distance, config.include_return_to_depot)
        )

    solution = Solution(routes, config.include_return_to_depot)
    stats = {
        "solver": "ortools",
        "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
        "metaheuristic": "GUIDED_LOCAL_SEARCH",
        "max_route_length": max(route_lengths) if route_lengths else 0,
        "fallback_used": False,
    }
    return solution, stats


def _fallback_solution(instance: Instance, config: AlgorithmConfig) -> Solution:
    fallback = GreedyBalancedAlgorithm(config).solve(instance).best
    return fallback


def _route_length(
    route: list[int],
    distance: list[list[Distance]],
    include_return_to_depot: bool,
) -> Distance:
    if len(route) <= 1:
        return 0.0
    length = 0.0
    for idx in range(len(route) - 1):
        length += distance[route[idx]][route[idx + 1]]
    if include_return_to_depot:
        length += distance[route[-1]][0]
    return length


def _scaled_distance(value: Distance, scale: int) -> int:
    return max(0, int(round(value * scale)))


def _set_time_limit(search_parameters: pywrapcp.RoutingSearchParameters, time_limit: float) -> None:
    capped = max(0.0, time_limit)
    seconds = int(capped)
    nanos = int((capped - seconds) * 1_000_000_000)
    search_parameters.time_limit.seconds = seconds
    search_parameters.time_limit.nanos = nanos
