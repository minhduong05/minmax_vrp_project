from __future__ import annotations

from ..models import Distance, Instance, Objective, Solution, route_lengths_objective


def has_positive_route_lengths(solution: Solution, instance: Instance) -> bool:
    return all(length > 0.0 for length in solution.route_lengths(instance))


def ensure_positive_route_lengths(solution: Solution, instance: Instance) -> Solution:
    """Return a feasible solution where every vehicle travels positive distance."""
    repaired = solution.copy()
    if has_positive_route_lengths(repaired, instance):
        return repaired
    if instance.k > instance.n:
        raise ValueError(
            "cannot assign positive routes when there are more vehicles than pickup points"
        )

    while True:
        lengths = repaired.route_lengths(instance)
        inactive_route = _first_nonpositive_route(lengths)
        if inactive_route is None:
            repaired.assert_feasible(instance)
            return repaired

        move = _best_activation_move(repaired, inactive_route, instance)
        if move is None:
            raise ValueError(
                "cannot repair solution so every vehicle has a positive-length route"
            )

        source_route, source_pos, insert_pos = move
        point = repaired.routes[source_route].pop(source_pos)
        repaired.routes[inactive_route].insert(insert_pos, point)


def _first_nonpositive_route(lengths: list[Distance]) -> int | None:
    for route_index, length in enumerate(lengths):
        if length <= 0.0:
            return route_index
    return None


def _best_activation_move(
    solution: Solution,
    target_route: int,
    instance: Instance,
) -> tuple[int, int, int] | None:
    best = None
    for source_route, route in enumerate(solution.routes):
        if source_route == target_route or len(route) <= 2:
            continue
        for source_pos in range(1, len(route)):
            point = route[source_pos]
            source_candidate = route[:source_pos] + route[source_pos + 1 :]
            source_length = solution.route_length(source_candidate, instance.distance)
            if source_length <= 0.0:
                continue

            target = solution.routes[target_route]
            for insert_pos in range(1, len(target) + 1):
                target_candidate = target[:insert_pos] + [point] + target[insert_pos:]
                target_length = solution.route_length(target_candidate, instance.distance)
                if target_length <= 0.0:
                    continue

                score = _activation_score(
                    solution,
                    source_route,
                    source_length,
                    target_route,
                    target_length,
                    instance,
                )
                if best is None or score < best[0]:
                    best = (score, source_route, source_pos, insert_pos)

    if best is None:
        return None
    _, source_route, source_pos, insert_pos = best
    return source_route, source_pos, insert_pos


def _activation_score(
    solution: Solution,
    source_route: int,
    source_length: Distance,
    target_route: int,
    target_length: Distance,
    instance: Instance,
) -> Objective:
    lengths = solution.route_lengths(instance)
    lengths[source_route] = source_length
    lengths[target_route] = target_length
    return route_lengths_objective(lengths)
