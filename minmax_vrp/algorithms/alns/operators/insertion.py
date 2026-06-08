from __future__ import annotations

import random
from heapq import nsmallest

from minmax_vrp.algorithms.alns.core.solution import Objective, Solution

Candidate = tuple[Objective, float, int, int]


def _route_subset(solution: Solution, customer: int, max_routes: int = 18, nearest_limit: int = 36) -> list[int]:
    """Small but high-quality set of routes to test for inserting ``customer``.

    Full insertion scans are expensive when K is large. For Min-Max VRP, good
    insertions usually happen in short routes or near already-related customers.
    We therefore combine:
    - empty routes, if any;
    - shortest routes, to improve balance;
    - the current longest route, to avoid ignoring it completely;
    - routes containing nearest neighbors of the customer.
    """
    k = solution.instance.k
    chosen: set[int] = set()

    # Empty routes must be considered to keep all K postmen active when required.
    for idx, route in enumerate(solution.routes):
        if len(route) == 1:
            chosen.add(idx)

    shortest_count = max(1, max_routes // 2)
    for idx in nsmallest(shortest_count, range(k), key=lambda r: solution.route_lengths[r]):
        chosen.add(idx)

    if k > 0:
        chosen.add(max(range(k), key=lambda r: solution.route_lengths[r]))

    for near in solution.instance.nearest_customers(customer, nearest_limit):
        loc = solution.customer_pos[near]
        if loc is not None:
            chosen.add(loc[0])
            if len(chosen) >= max_routes:
                break

    if len(chosen) < min(max_routes, k):
        for idx in nsmallest(max_routes, range(k), key=lambda r: solution.route_lengths[r]):
            chosen.add(idx)
            if len(chosen) >= max_routes:
                break

    return list(chosen)


def _positions_for_route(solution: Solution, route_idx: int, customer: int, max_positions: int = 24) -> list[int]:
    """Candidate positions in one route.

    If the route is short, scan all positions. If it is long, test positions near
    nodes that are geometrically close to the customer plus the route endpoints.
    """
    route = solution.routes[route_idx]
    if len(route) <= max_positions + 1:
        return list(range(1, len(route) + 1))

    positions: set[int] = {1, len(route)}
    dist_row = solution.instance.distance[customer]
    nearest_pos = nsmallest(
        max(1, max_positions // 2),
        range(1, len(route)),
        key=lambda pos: dist_row[route[pos]],
    )
    for pos in nearest_pos:
        positions.add(pos)
        positions.add(pos + 1)
    return sorted(p for p in positions if 1 <= p <= len(route))


def _candidate_insertions(
    solution: Solution,
    customer: int,
    *,
    max_routes: int = 18,
    max_positions_per_route: int = 24,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for r_idx in _route_subset(solution, customer, max_routes=max_routes):
        for pos in _positions_for_route(solution, r_idx, customer, max_positions=max_positions_per_route):
            delta = solution.insertion_delta(r_idx, pos, customer)
            obj = solution.objective_after_delta(r_idx, delta)
            candidates.append((obj, delta, r_idx, pos))

    # Safety fallback: should rarely happen, but keeps the operator robust.
    if not candidates:
        for r_idx, route in enumerate(solution.routes):
            for pos in range(1, len(route) + 1):
                delta = solution.insertion_delta(r_idx, pos, customer)
                candidates.append((solution.objective_after_delta(r_idx, delta), delta, r_idx, pos))
    return candidates


def _pop_unassigned_by_index(solution: Solution, idx: int) -> int:
    """O(1) unordered pop from unassigned list."""
    customer = solution.unassigned[idx]
    solution.unassigned[idx] = solution.unassigned[-1]
    solution.unassigned.pop()
    return customer


def _iter_unassigned_sample(solution: Solution, rng: random.Random, limit: int):
    """Yield (index, customer) pairs, optionally sampled for speed."""
    m = len(solution.unassigned)
    if m <= limit:
        yield from enumerate(solution.unassigned)
        return
    # Always include a random subset. Repair quality remains good because ALNS
    # repeats many iterations, while runtime drops from O(q^2) toward O(q).
    for idx in rng.sample(range(m), limit):
        yield idx, solution.unassigned[idx]


class GreedyMinMaxInsertion:
    name = "greedy_minmax_insertion"

    def __init__(self, max_routes: int = 14, max_positions_per_route: int = 18, customer_sample_size: int = 32):
        self.max_routes = max_routes
        self.max_positions_per_route = max_positions_per_route
        self.customer_sample_size = customer_sample_size

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        repaired = solution.copy()
        rng.shuffle(repaired.unassigned)
        while repaired.unassigned:
            best: tuple[Objective, float, int, int, int] | None = None
            best_unassigned_idx = 0
            for idx, customer in _iter_unassigned_sample(repaired, rng, self.customer_sample_size):
                obj, delta, r_idx, pos = min(
                    _candidate_insertions(
                        repaired,
                        customer,
                        max_routes=self.max_routes,
                        max_positions_per_route=self.max_positions_per_route,
                    ),
                    key=lambda x: (x[0], x[1]),
                )
                item = (obj, delta, r_idx, pos, customer)
                if best is None or item[:2] < best[:2]:
                    best = item
                    best_unassigned_idx = idx
            assert best is not None
            _, _, r_idx, pos, customer = best
            _pop_unassigned_by_index(repaired, best_unassigned_idx)
            repaired.insert_customer(r_idx, pos, customer)
        return repaired


class RegretInsertion:
    name = "regret_insertion"

    def __init__(self, k: int = 2, max_routes: int = 14, max_positions_per_route: int = 18, customer_sample_size: int = 36):
        self.k = max(2, k)
        self.max_routes = max_routes
        self.max_positions_per_route = max_positions_per_route
        self.customer_sample_size = customer_sample_size

    @staticmethod
    def _objective_gap(a: Objective, b: Objective) -> float:
        """A scalar gap used only for regret ranking.

        The actual move selection still uses the lexicographic objective. This
        scalar makes regret stable and avoids the previous bug where tuple
        comparison could prefer a worse best insertion when regrets tied.
        """
        a_max = a[0][0] if a[0] else 0.0
        b_max = b[0][0] if b[0] else 0.0
        return (a_max - b_max) * 1_000_000.0 + (a[1] - b[1])

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        repaired = solution.copy()
        while repaired.unassigned:
            best_choice: tuple[float, Objective, float, int, int, int] | None = None
            best_unassigned_idx = 0
            for idx, customer in _iter_unassigned_sample(repaired, rng, self.customer_sample_size):
                cands = sorted(
                    _candidate_insertions(
                        repaired,
                        customer,
                        max_routes=self.max_routes,
                        max_positions_per_route=self.max_positions_per_route,
                    ),
                    key=lambda x: (x[0], x[1]),
                )
                best = cands[0]
                kth = cands[min(self.k - 1, len(cands) - 1)]
                regret = self._objective_gap(kth[0], best[0])
                # Rank by larger regret, then better best objective, then smaller delta.
                item = (regret, best[0], best[1], best[2], best[3], customer)
                if (
                    best_choice is None
                    or regret > best_choice[0]
                    or (regret == best_choice[0] and (best[0], best[1]) < (best_choice[1], best_choice[2]))
                ):
                    best_choice = item
                    best_unassigned_idx = idx
            assert best_choice is not None
            _, _, _, r_idx, pos, customer = best_choice
            _pop_unassigned_by_index(repaired, best_unassigned_idx)
            repaired.insert_customer(r_idx, pos, customer)
        return repaired


class BalancedInsertion:
    name = "balanced_insertion"

    def __init__(self, max_routes: int = 10, max_positions_per_route: int = 16, customer_sample_size: int = 32):
        self.max_routes = max_routes
        self.max_positions_per_route = max_positions_per_route
        self.customer_sample_size = customer_sample_size

    def __call__(self, solution: Solution, rng: random.Random) -> Solution:
        repaired = solution.copy()
        rng.shuffle(repaired.unassigned)
        while repaired.unassigned:
            route_order = nsmallest(self.max_routes, range(len(repaired.routes)), key=lambda idx: repaired.route_lengths[idx])
            best: tuple[Objective, float, int, int, int] | None = None
            best_unassigned_idx = 0
            for idx, customer in _iter_unassigned_sample(repaired, rng, self.customer_sample_size):
                # Combine short routes with related routes, then keep only the best candidate.
                routes = set(route_order)
                routes.update(_route_subset(repaired, customer, max_routes=max(4, self.max_routes // 2)))
                for r_idx in routes:
                    for pos in _positions_for_route(repaired, r_idx, customer, self.max_positions_per_route):
                        delta = repaired.insertion_delta(r_idx, pos, customer)
                        obj = repaired.objective_after_delta(r_idx, delta)
                        item = (obj, delta, r_idx, pos, customer)
                        if best is None or item[:2] < best[:2]:
                            best = item
                            best_unassigned_idx = idx
            assert best is not None
            _, _, r_idx, pos, customer = best
            _pop_unassigned_by_index(repaired, best_unassigned_idx)
            repaired.insert_customer(r_idx, pos, customer)
        return repaired

