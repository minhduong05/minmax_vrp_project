import random
from dataclasses import dataclass

from ...models import Distance, Instance, Solution
from .operators_utils import removal_saving, remove_pickup_point


@dataclass(frozen=True)
class RandomRemoval:
    name: str = "random_removal"

    def __call__(self, solution: Solution, instance: Instance, q: int, rng: random.Random) -> tuple[Solution, list[int]]:
        partial = solution.copy()
        points = partial.all_pickup_points()
        removed = rng.sample(points, k=min(q, len(points)))
        for point in removed:
            remove_pickup_point(partial, point)
        return partial, removed


@dataclass(frozen=True)
class WorstRemoval:
    """Remove pickup points with the largest saving if removed.

    For Min-Max VRP, set focus_longest=True so the operator attacks the current
    longest route first.
    """

    focus_longest: bool = True
    noise: float = 0.15
    name: str = "worst_removal"

    def __call__(self, solution: Solution, instance: Instance, q: int, rng: random.Random) -> tuple[Solution, list[int]]:
        partial = solution.copy()
        removed: list[int] = []
        q = min(q, instance.n)
        while len(removed) < q and partial.all_pickup_points():
            lengths = partial.route_lengths(instance)
            route_order = list(range(len(partial.routes)))
            if self.focus_longest:
                route_order = _routes_by_decreasing_length(lengths)
            candidates: list[tuple[float, int, int]] = []  # score, r_idx, pos
            for r_idx in route_order:
                route = partial.routes[r_idx]
                for pos in range(1, len(route)):
                    saving = removal_saving(route, pos, instance)
                    noisy = saving * (1.0 + rng.uniform(-self.noise, self.noise))
                    bonus = lengths[r_idx] if self.focus_longest else 0
                    candidates.append((noisy + 0.001 * bonus, r_idx, pos))
                if self.focus_longest and candidates:
                    break
            if not candidates:
                break
            _, r_idx, pos = _best_scored_position(candidates)
            removed.append(partial.routes[r_idx].pop(pos))
        rng.shuffle(removed)
        return partial, removed


@dataclass(frozen=True)
class LongestRouteRemoval:
    name: str = "longest_route_removal"

    def __call__(self, solution: Solution, instance: Instance, q: int, rng: random.Random) -> tuple[Solution, list[int]]:
        partial = solution.copy()
        removed: list[int] = []
        while len(removed) < q and partial.all_pickup_points():
            lengths = partial.route_lengths(instance)
            longest_idx = _longest_route_index(lengths)
            route = partial.routes[longest_idx]
            if len(route) <= 1:
                break
            # Remove the most expensive pickup point in the current longest route.
            pos = _most_expensive_position(route, instance)
            removed.append(route.pop(pos))
        rng.shuffle(removed)
        return partial, removed


@dataclass(frozen=True)
class RouteRemoval:
    """Remove pickup points from one selected route.

    Prefer long routes because the project objective is min-max.
    """

    prefer_longest_probability: float = 0.75
    name: str = "route_removal"

    def __call__(self, solution: Solution, instance: Instance, q: int, rng: random.Random) -> tuple[Solution, list[int]]:
        partial = solution.copy()
        non_empty = []
        for route_index, route in enumerate(partial.routes):
            if len(route) > 1:
                non_empty.append(route_index)
        if not non_empty:
            return partial, []
        if rng.random() < self.prefer_longest_probability:
            lengths = partial.route_lengths(instance)
            r_idx = _longest_non_empty_route(non_empty, lengths)
        else:
            r_idx = rng.choice(non_empty)
        points = partial.routes[r_idx][1:]
        if len(points) > q:
            removed = rng.sample(points, q)
            removed_set = set(removed)
            kept_points = [0]
            for point in points:
                if point not in removed_set:
                    kept_points.append(point)
            partial.routes[r_idx] = kept_points
        else:
            removed = points[:]
            partial.routes[r_idx] = [0]
        rng.shuffle(removed)
        return partial, removed


@dataclass(frozen=True)
class RelatedRemoval:
    """Remove pickup points close to a randomly chosen seed point."""

    randomization_power: float = 4.0
    name: str = "related_removal"

    def __call__(self, solution: Solution, instance: Instance, q: int, rng: random.Random) -> tuple[Solution, list[int]]:
        partial = solution.copy()
        points = partial.all_pickup_points()
        if not points:
            return partial, []
        seed = rng.choice(points)
        removed = [seed]
        remove_pickup_point(partial, seed)
        while len(removed) < q:
            remaining = partial.all_pickup_points()
            if not remaining:
                break
            anchor = rng.choice(removed)
            def distance_from_anchor(point: int) -> Distance:
                return instance.distance[anchor][point]

            remaining.sort(key=distance_from_anchor)
            # Biased-random choice among nearest pickup points.
            idx = int((rng.random() ** self.randomization_power) * len(remaining))
            chosen = remaining[min(idx, len(remaining) - 1)]
            remove_pickup_point(partial, chosen)
            removed.append(chosen)
        rng.shuffle(removed)
        return partial, removed


def _routes_by_decreasing_length(lengths: list[Distance]) -> list[int]:
    route_order = list(range(len(lengths)))

    def route_length(route_index: int) -> Distance:
        return lengths[route_index]

    route_order.sort(key=route_length, reverse=True)
    return route_order


def _best_scored_position(candidates: list[tuple[float, int, int]]) -> tuple[float, int, int]:
    best_candidate = candidates[0]
    for candidate in candidates[1:]:
        if candidate[0] > best_candidate[0]:
            best_candidate = candidate
    return best_candidate


def _longest_route_index(lengths: list[Distance]) -> int:
    longest = 0
    for route_index in range(1, len(lengths)):
        if lengths[route_index] > lengths[longest]:
            longest = route_index
    return longest


def _longest_non_empty_route(non_empty_routes: list[int], lengths: list[Distance]) -> int:
    longest = non_empty_routes[0]
    for route_index in non_empty_routes[1:]:
        if lengths[route_index] > lengths[longest]:
            longest = route_index
    return longest


def _most_expensive_position(route: list[int], instance: Instance) -> int:
    best_position = 1
    best_saving = removal_saving(route, best_position, instance)
    for position in range(2, len(route)):
        saving = removal_saving(route, position, instance)
        if saving > best_saving:
            best_saving = saving
            best_position = position
    return best_position


def default_destroy_operators() -> list:
    return [
        RandomRemoval(),
        WorstRemoval(focus_longest=True),
        LongestRouteRemoval(),
        RelatedRemoval(),
        RouteRemoval(),
    ]
