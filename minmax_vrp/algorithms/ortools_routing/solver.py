from __future__ import annotations

import time

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from ...models import Distance, Instance, Solution
from ..base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
from ..route_constraints import ensure_positive_route_lengths


class OrToolsRoutingAlgorithm(SolverAlgorithm):
    name = "ortools_routing"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance: Instance) -> AlgorithmResult:
        start = time.perf_counter()
        solution, stats = _solve_with_ortools(instance, self.config)
        if solution is None:
            solution = _fallback_solution(instance)
            stats["fallback_used"] = True
        solution = ensure_positive_route_lengths(solution, instance)
        solution.assert_feasible(instance)
        stats["max_route_length"] = solution.evaluate(instance).max_route_length
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
    distance_scale = _distance_scale(instance)
    fallback_upper_bound = _upper_bound_solution(instance)
    manager = pywrapcp.RoutingIndexManager(instance.n + 1, instance.k, 0)
    routing = pywrapcp.RoutingModel(manager)

    max_distance = 0
    for row in instance.distance:
        row_max = max(_scaled_distance(value, distance_scale) for value in row)
        if row_max > max_distance:
            max_distance = row_max

    def transit_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        if to_node == 0:
            return 0
        return _scaled_distance(instance.distance[from_node][to_node], distance_scale)

    transit_callback_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    crude_horizon = max(1, instance.n * max_distance)
    upper_bound_horizon = _scaled_solution_max_route_length(
        fallback_upper_bound, instance.distance, distance_scale
    )
    horizon = max(1, min(crude_horizon, upper_bound_horizon))
    routing.AddDimension(
        transit_callback_index,
        0,
        horizon,
        True,
        "Distance",
    )
    distance_dimension = routing.GetDimensionOrDie("Distance")
    # Minimize max route first. Arc costs remain active, so total distance breaks
    # ties after the route span term dominates any possible total-cost difference.
    distance_dimension.SetGlobalSpanCostCoefficient((instance.k * horizon) + 1)

    if instance.k <= instance.n:
        def visit_callback(from_index: int) -> int:
            return 0 if manager.IndexToNode(from_index) == 0 else 1

        visit_callback_index = routing.RegisterUnaryTransitCallback(visit_callback)
        routing.AddDimension(
            visit_callback_index,
            0,
            instance.n,
            True,
            "VisitCount",
        )
        visit_count_dimension = routing.GetDimensionOrDie("VisitCount")
        for vehicle_idx in range(instance.k):
            visit_count_dimension.CumulVar(routing.End(vehicle_idx)).SetMin(1)

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
            "distance_scale": distance_scale,
            "horizon": horizon,
            "crude_horizon": crude_horizon,
            "non_empty_routes_enforced": instance.k <= instance.n,
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
        route_lengths.append(_route_length(route, instance.distance))

    solution = Solution(routes)
    stats = {
        "solver": "ortools",
        "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
        "metaheuristic": "GUIDED_LOCAL_SEARCH",
        "max_route_length": max(route_lengths) if route_lengths else 0,
        "fallback_used": False,
        "distance_scale": distance_scale,
        "horizon": horizon,
        "crude_horizon": crude_horizon,
        "non_empty_routes_enforced": instance.k <= instance.n,
    }
    return solution, stats


def _fallback_solution(instance: Instance) -> Solution:
    routes = [[0] for _ in range(instance.k)]

    for point in instance.pickup_points:
        best_choice: tuple[tuple[Distance, Distance, Distance], int, int] | None = None
        for route_index, route in enumerate(routes):
            for insert_pos in range(1, len(route) + 1):
                candidate = route[:insert_pos] + [point] + route[insert_pos:]
                score = _candidate_score(routes, route_index, candidate, instance)
                if best_choice is None or score < best_choice[0]:
                    best_choice = (score, route_index, insert_pos)

        assert best_choice is not None
        _, selected_route, selected_pos = best_choice
        routes[selected_route].insert(selected_pos, point)

    return Solution(routes)


def _upper_bound_solution(instance: Instance) -> Solution:
    solution = _fallback_solution(instance)
    if instance.k > instance.n:
        return solution
    return ensure_positive_route_lengths(solution, instance)


def _candidate_score(
    routes: list[list[int]],
    changed_route_index: int,
    changed_route: list[int],
    instance: Instance,
) -> tuple[Distance, Distance, Distance]:
    lengths = []
    for route_index, route in enumerate(routes):
        if route_index == changed_route_index:
            lengths.append(_route_length(changed_route, instance.distance))
        else:
            lengths.append(_route_length(route, instance.distance))
    max_length = max(lengths) if lengths else 0.0
    total = sum(lengths)
    balance = max_length - min(lengths) if lengths else 0.0
    return (max_length, total, balance)


def _route_length(route: list[int], distance: list[list[Distance]]) -> Distance:
    if len(route) <= 1:
        return 0.0
    length = 0.0
    for idx in range(len(route) - 1):
        length += distance[route[idx]][route[idx + 1]]
    return length


def _scaled_solution_max_route_length(
    solution: Solution,
    distance: list[list[Distance]],
    scale: int,
) -> int:
    max_length = 0
    for route in solution.routes:
        route_length = 0
        for idx in range(len(route) - 1):
            route_length += _scaled_distance(distance[route[idx]][route[idx + 1]], scale)
        max_length = max(max_length, route_length)
    return max_length


def _scaled_distance(value: Distance, scale: int) -> int:
    return max(0, int(round(value * scale)))


def _distance_scale(instance: Instance) -> int:
    has_fractional_distance = any(
        value != int(value)
        for row in instance.distance
        for value in row
    )
    return 1000 if has_fractional_distance else 1


def _set_time_limit(search_parameters: pywrapcp.RoutingSearchParameters, time_limit: float) -> None:
    capped = max(0.0, time_limit)
    seconds = int(capped)
    nanos = int((capped - seconds) * 1_000_000_000)
    search_parameters.time_limit.seconds = seconds
    search_parameters.time_limit.nanos = nanos
