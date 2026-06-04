from __future__ import annotations

import copy
import sys
import time
from collections import deque
from typing import Iterable

from ...models import Distance

Objective = tuple[Distance, Distance, Distance]


def read_input():
    tokens = sys.stdin.read().replace("\ufeff", "").split()
    if not tokens:
        return None

    n = int(tokens[0])
    k = int(tokens[1])
    size = n + 1
    values = tokens[2:]
    if len(values) != size * size:
        raise ValueError(f"expected {size * size} distance values, got {len(values)}")

    distance = []
    idx = 0
    for _ in range(size):
        row = []
        for _ in range(size):
            row.append(float(values[idx]))
            idx += 1
        distance.append(row)

    return n, k, distance


def route_lenght(
    route: list[int],
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> Distance:
    if len(route) <= 1:
        return 0.0

    length = 0.0
    for i in range(len(route) - 1):
        length += d[route[i]][route[i + 1]]
    if include_return_to_depot:
        length += d[route[-1]][0]
    return length


def all_lengths(
    routes: list[list[int]],
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> list[Distance]:
    return [route_lenght(route, d, include_return_to_depot) for route in routes]


def objective_from_lengths(lengths: Iterable[Distance]) -> Objective:
    values = list(lengths)
    if not values:
        return (0.0, 0.0, 0.0)
    max_len = max(values)
    return (max_len, sum(values), max_len - min(values))


def objective(
    routes: list[list[int]],
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> Objective:
    return objective_from_lengths(all_lengths(routes, d, include_return_to_depot))


def longest_route(
    routes: list[list[int]],
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> Distance:
    return objective(routes, d, include_return_to_depot)[0]


def insertion_delta(
    route: list[int],
    point: int,
    position: int,
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> Distance:
    prev = route[position - 1]
    if position < len(route):
        next_node = route[position]
        return d[prev][point] + d[point][next_node] - d[prev][next_node]
    if include_return_to_depot:
        return d[prev][point] + d[point][0] - d[prev][0]
    return d[prev][point]


def init(
    n: int,
    k: int,
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
) -> list[list[int]]:
    routes = [[0] for _ in range(k)]
    lengths = [0.0] * k
    points = sorted(range(1, n + 1), key=lambda point: d[0][point], reverse=True)

    for point in points:
        best = None
        total = sum(lengths)
        for route_idx, route in enumerate(routes):
            other_max = max(
                (lengths[idx] for idx in range(k) if idx != route_idx), default=0.0
            )
            for position in range(1, len(route) + 1):
                delta = insertion_delta(route, point, position, d, include_return_to_depot)
                new_len = lengths[route_idx] + delta
                score = (max(other_max, new_len), total + delta, new_len)
                if best is None or score < best[0]:
                    best = (score, route_idx, position, delta)

        if best is None:
            continue
        _, route_idx, position, delta = best
        routes[route_idx].insert(position, point)
        lengths[route_idx] += delta

    return routes


def apply_relocate(
    routes: list[list[int]],
    src: int,
    src_pos: int,
    dst: int,
    dst_pos: int,
) -> list[list[int]]:
    new_routes = copy.deepcopy(routes)
    point = new_routes[src].pop(src_pos)
    if src == dst and dst_pos >= src_pos:
        dst_pos -= 1
    new_routes[dst].insert(dst_pos + 1, point)
    return new_routes


def apply_swap(
    routes: list[list[int]],
    r1: int,
    pos1: int,
    r2: int,
    pos2: int,
) -> list[list[int]]:
    new_routes = copy.deepcopy(routes)
    new_routes[r1][pos1], new_routes[r2][pos2] = new_routes[r2][pos2], new_routes[r1][pos1]
    return new_routes


def apply_reverse(routes: list[list[int]], route_idx: int, start: int, end: int):
    new_routes = copy.deepcopy(routes)
    new_routes[route_idx][start : end + 1] = reversed(
        new_routes[route_idx][start : end + 1]
    )
    return new_routes


def generative_candidates(
    routes: list[list[int]],
    d: list[list[Distance]],
    max_candidates: int = 200,
    include_return_to_depot: bool = True,
    deadline: float | None = None,
):
    lengths = all_lengths(routes, d, include_return_to_depot)
    longest_idx = max(range(len(routes)), key=lambda idx: lengths[idx])
    candidates = []

    src = longest_idx
    for src_pos in range(1, len(routes[src])):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        point = routes[src][src_pos]
        for dst in range(len(routes)):
            if dst == src:
                continue
            for dst_pos in range(len(routes[dst])):
                new_routes = apply_relocate(routes, src, src_pos, dst, dst_pos)
                new_obj = objective(new_routes, d, include_return_to_depot)
                tabu_attr = ("relocate", point, dst)
                candidates.append((new_obj, "relocate", tabu_attr, (src, src_pos, dst, dst_pos)))

    for pos1 in range(1, len(routes[src])):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        point1 = routes[src][pos1]
        for dst in range(len(routes)):
            if dst == src:
                continue
            for pos2 in range(1, len(routes[dst])):
                point2 = routes[dst][pos2]
                new_routes = apply_swap(routes, src, pos1, dst, pos2)
                new_obj = objective(new_routes, d, include_return_to_depot)
                tabu_attr = ("swap", min(point1, point2), max(point1, point2))
                candidates.append((new_obj, "swap", tabu_attr, (src, pos1, dst, pos2)))

    for start in range(1, len(routes[src]) - 1):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        for end in range(start + 1, len(routes[src])):
            new_routes = apply_reverse(routes, src, start, end)
            new_obj = objective(new_routes, d, include_return_to_depot)
            tabu_attr = ("reverse", tuple(routes[src][start : end + 1]))
            candidates.append((new_obj, "reverse", tabu_attr, (src, start, end)))

    candidates.sort(key=lambda item: item[0])
    return candidates[:max_candidates]


def tabu_search(
    n: int,
    k: int,
    d: list[list[Distance]],
    max_inter: int = 1000,
    tenure: int = 7,
    max_candidates: int = 200,
    include_return_to_depot: bool = True,
    deadline: float | None = None,
):
    routes = init(n, k, d, include_return_to_depot)
    best_routes = copy.deepcopy(routes)
    best_obj = objective(best_routes, d, include_return_to_depot)

    tabu_set = set()
    tabu_queue = deque()
    iterations_done = 0

    for _ in range(max_inter):
        if deadline is not None and time.perf_counter() >= deadline:
            break
        candidates = generative_candidates(
            routes, d, max_candidates, include_return_to_depot, deadline
        )
        if not candidates:
            break

        chosen = candidates[0]
        for candidate in candidates:
            new_obj, _, tabu_attr, _ = candidate
            if tabu_attr not in tabu_set or new_obj < best_obj:
                chosen = candidate
                break

        new_obj, move_type, tabu_attr, move_params = chosen
        if move_type == "relocate":
            routes = apply_relocate(routes, *move_params)
        elif move_type == "swap":
            routes = apply_swap(routes, *move_params)
        elif move_type == "reverse":
            routes = apply_reverse(routes, *move_params)

        current_obj = objective(routes, d, include_return_to_depot)
        if current_obj < best_obj:
            best_obj = current_obj
            best_routes = copy.deepcopy(routes)

        tabu_queue.append(tabu_attr)
        tabu_set.add(tabu_attr)
        if len(tabu_queue) > tenure:
            old_attr = tabu_queue.popleft()
            tabu_set.discard(old_attr)
        iterations_done += 1

    return best_routes, best_obj[0], iterations_done


def local_clear(
    routes: list[list[int]],
    d: list[list[Distance]],
    include_return_to_depot: bool = True,
):
    routes = copy.deepcopy(routes)
    improved = True
    while improved:
        improved = False
        for route_idx, route in enumerate(routes):
            if len(route) < 4:
                continue
            old_len = route_lenght(route, d, include_return_to_depot)
            best_route = route
            best_len = old_len
            for start in range(1, len(route) - 1):
                for end in range(start + 1, len(route)):
                    new_route = route[:start] + route[start : end + 1][::-1] + route[end + 1 :]
                    new_len = route_lenght(new_route, d, include_return_to_depot)
                    if new_len < best_len:
                        best_route = new_route
                        best_len = new_len

            if best_len < old_len:
                routes[route_idx] = best_route
                improved = True
    return routes


def output(routes, d, include_return_to_depot: bool = True):
    print(len(routes))
    for route in routes:
        print("length:", route_lenght(route, d, include_return_to_depot))
        print(len(route))
        print(" ".join(map(str, route)))


def main():
    parsed = read_input()
    if parsed is None:
        return
    n, k, d = parsed
    best_routes, _, _ = tabu_search(n, k, d)
    best_routes = local_clear(best_routes, d)
    output(best_routes, d)


if __name__ == "__main__":
    main()
