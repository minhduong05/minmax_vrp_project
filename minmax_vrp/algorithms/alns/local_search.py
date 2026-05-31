import random
import time

from ...models import Instance, Solution, better


def improve(
    solution: Solution,
    instance: Instance,
    rng: random.Random,
    max_rounds: int = 2,
    deadline: float | None = None,
) -> Solution:
    """Small local search after repair.

    Designed for the min-max objective:
    1. Try relocating pickup points from the current longest route.
    2. Try swapping a pickup point in the longest route with another route.
    3. Run limited 2-opt inside long routes.
    """
    current = solution.copy()
    for _ in range(max_rounds):
        if _out_of_time(deadline):
            break
        changed = False
        for step in (_relocate_from_longest, _swap_with_longest, _two_opt_long_routes):
            if _out_of_time(deadline):
                break
            candidate = step(current, instance, rng, deadline)
            if better(candidate, current, instance):
                current = candidate
                changed = True
        if not changed:
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
        temp = solution.copy()
        temp.routes[longest].pop(pos)
        for r_idx, target_route in enumerate(temp.routes):
            if _out_of_time(deadline):
                break
            for insert_pos in range(1, len(target_route) + 1):
                cand = temp.copy()
                cand.routes[r_idx].insert(insert_pos, point)
                if better(cand, best, instance):
                    best = cand
    return best


def _swap_with_longest(
    solution: Solution, instance: Instance, rng: random.Random, deadline: float | None
) -> Solution:
    best = solution.copy()
    lengths = solution.route_lengths(instance)
    if not lengths:
        return best
    longest = _longest_route_index(lengths)
    long_positions = list(range(1, len(solution.routes[longest])))
    rng.shuffle(long_positions)
    long_positions = long_positions[: min(15, len(long_positions))]

    other_routes = []
    for route_index, route in enumerate(solution.routes):
        if route_index != longest and len(route) > 1:
            other_routes.append(route_index)
    other_routes.sort(key=lambda route_index: lengths[route_index])
    for pos_a in long_positions:
        if _out_of_time(deadline):
            break
        for r_idx in other_routes[: min(10, len(other_routes))]:
            if _out_of_time(deadline):
                break
            positions_b = list(range(1, len(solution.routes[r_idx])))
            rng.shuffle(positions_b)
            for pos_b in positions_b[: min(10, len(positions_b))]:
                cand = solution.copy()
                cand.routes[longest][pos_a], cand.routes[r_idx][pos_b] = (
                    cand.routes[r_idx][pos_b],
                    cand.routes[longest][pos_a],
                )
                if better(cand, best, instance):
                    best = cand
    return best


def _two_opt_long_routes(
    solution: Solution, instance: Instance, rng: random.Random, deadline: float | None
) -> Solution:
    best = solution.copy()
    lengths = solution.route_lengths(instance)
    # Focus on the few longest routes to keep runtime controlled on N=1000.
    route_order = _routes_by_decreasing_length(lengths)
    route_order = route_order[: min(5, len(lengths))]
    for r_idx in route_order:
        if _out_of_time(deadline):
            break
        route = solution.routes[r_idx]
        m = len(route)
        if m <= 4:
            continue
        # Sample candidate pairs rather than full O(m^2) for large routes.
        pairs: list[tuple[int, int]] = []
        max_pairs = min(80, (m - 1) * (m - 2) // 2)
        for _ in range(max_pairs):
            i = rng.randint(1, m - 2)
            j = rng.randint(i + 1, m - 1)
            pairs.append((i, j))
        for i, j in pairs:
            if _out_of_time(deadline):
                break
            cand = solution.copy()
            cand.routes[r_idx][i : j + 1] = reversed(cand.routes[r_idx][i : j + 1])
            if better(cand, best, instance):
                best = cand
    return best


def _out_of_time(deadline: float | None) -> bool:
    return deadline is not None and time.perf_counter() >= deadline


def _longest_route_index(lengths: list[int]) -> int:
    longest = 0
    for route_index in range(1, len(lengths)):
        if lengths[route_index] > lengths[longest]:
            longest = route_index
    return longest


def _routes_by_decreasing_length(lengths: list[int]) -> list[int]:
    route_order = list(range(len(lengths)))

    def route_length(route_index: int) -> int:
        return lengths[route_index]

    route_order.sort(key=route_length, reverse=True)
    return route_order
