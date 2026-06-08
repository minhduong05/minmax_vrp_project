from __future__ import annotations

import random
from dataclasses import dataclass

from minmax_vrp.algorithms.alns.core.solution import Solution


@dataclass(frozen=True)
class DestroyConfig:
    min_remove: int = 1
    max_remove_fraction: float = 0.15

    def removal_count(self, solution: Solution, rng: random.Random) -> int:
        total = sum(len(r) - 1 for r in solution.routes)
        if total <= 0:
            return 0
        max_remove = max(self.min_remove, int(total * self.max_remove_fraction))
        max_remove = min(max_remove, total)
        return rng.randint(self.min_remove, max_remove)


def _nonempty_customer_positions(solution: Solution) -> list[tuple[int, int, int]]:
    return list(solution.iter_customers())


class RandomRemoval:
    name = "random_removal"

    def __init__(self, config: DestroyConfig | None = None):
        self.config = config or DestroyConfig()

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        destroyed = solution.copy()
        q = self.config.removal_count(destroyed, rng)
        customers = [c for _, _, c in _nonempty_customer_positions(destroyed)]
        rng.shuffle(customers)
        for customer in customers[:q]:
            destroyed.remove_customer(customer, add_to_unassigned=True)
        return destroyed


class WorstRemoval:
    """Remove customers with the largest saving when removed.

    If focus_longest=True, only considers customers from the longest routes first,
    which is more aligned with Min-Max VRP than total-distance CVRP.
    """

    name = "worst_removal"

    def __init__(self, config: DestroyConfig | None = None, focus_longest: bool = True):
        self.config = config or DestroyConfig()
        self.focus_longest = focus_longest

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        destroyed = solution.copy()
        q = self.config.removal_count(destroyed, rng)
        for _ in range(q):
            positions = _nonempty_customer_positions(destroyed)
            if not positions:
                break
            if self.focus_longest:
                threshold = sorted(destroyed.route_lengths, reverse=True)[min(2, len(destroyed.route_lengths) - 1)]
                positions = [(r, p, c) for r, p, c in positions if destroyed.route_lengths[r] >= threshold]
            scored = []
            for r_idx, pos, customer in positions:
                saving = -destroyed.removal_delta(r_idx, pos)
                # Small random noise avoids deterministic cycling.
                scored.append((saving * (0.9 + 0.2 * rng.random()), r_idx, pos, customer))
            _, r_idx, pos, _ = max(scored, key=lambda x: x[0])
            destroyed.remove_at(r_idx, pos, add_to_unassigned=True)
        return destroyed


class LongestRouteRemoval:
    name = "longest_route_removal"

    def __init__(self, config: DestroyConfig | None = None):
        self.config = config or DestroyConfig()

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        destroyed = solution.copy()
        q = self.config.removal_count(destroyed, rng)
        for _ in range(q):
            candidates = [idx for idx, r in enumerate(destroyed.routes) if len(r) > 1]
            if not candidates:
                break
            r_idx = max(candidates, key=lambda idx: destroyed.route_lengths[idx])
            pos = rng.randrange(1, len(destroyed.routes[r_idx]))
            destroyed.remove_at(r_idx, pos, add_to_unassigned=True)
        return destroyed


class RouteRemoval:
    """Remove all or part of a route, preferring long routes."""

    name = "route_removal"

    def __init__(self, config: DestroyConfig | None = None, partial: bool = True):
        self.config = config or DestroyConfig()
        self.partial = partial

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        destroyed = solution.copy()
        candidates = [idx for idx, r in enumerate(destroyed.routes) if len(r) > 1]
        if not candidates:
            return destroyed
        top = sorted(candidates, key=lambda idx: destroyed.route_lengths[idx], reverse=True)[: max(1, len(candidates) // 4)]
        r_idx = rng.choice(top)
        route_customers = destroyed.routes[r_idx][1:]
        rng.shuffle(route_customers)
        q = len(route_customers) if not self.partial else min(len(route_customers), self.config.removal_count(destroyed, rng))
        for customer in route_customers[:q]:
            destroyed.remove_customer(customer, add_to_unassigned=True)
        return destroyed


class RelatedRemoval:
    """Shaw-style removal: remove geometrically related customers."""

    name = "related_removal"

    def __init__(self, config: DestroyConfig | None = None):
        self.config = config or DestroyConfig()

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        destroyed = solution.copy()
        positions = _nonempty_customer_positions(destroyed)
        if not positions:
            return destroyed
        q = self.config.removal_count(destroyed, rng)
        seed = rng.choice(positions)[2]
        dist = destroyed.instance.distance
        related = sorted([c for _, _, c in positions], key=lambda c: dist[seed][c])
        # Biased randomization: mostly close customers, sometimes farther ones.
        selected: list[int] = []
        pool = related[:]
        while pool and len(selected) < q:
            idx = int((rng.random() ** 2) * len(pool))
            selected.append(pool.pop(idx))
        for customer in selected:
            destroyed.remove_customer(customer, add_to_unassigned=True)
        return destroyed

