from __future__ import annotations

import random
from heapq import nsmallest

from minmax_vrp.algorithms.alns.core.instance import Instance
from minmax_vrp.algorithms.alns.core.solution import Solution


def balanced_nearest_seed(instance: Instance, rng: random.Random | None = None) -> Solution:
    """Fast feasible constructor for large Min-Max VRP instances.

    It activates all routes with farthest-from-depot seeds, then inserts remaining
    customers into a small set of short candidate routes. This is much faster than
    scanning all K routes and all positions for every customer, while still giving
    a balanced initial solution for ALNS.
    """
    rng = rng or random.Random()
    customers = set(range(1, instance.n + 1))
    routes = [[0] for _ in range(instance.k)]

    seeds = sorted(customers, key=lambda c: instance.d(0, c), reverse=True)[: min(instance.k, instance.n)]
    for idx, customer in enumerate(seeds):
        routes[idx].append(customer)
        customers.remove(customer)

    sol = Solution(instance, routes)

    remaining = list(customers)
    rng.shuffle(remaining)
    remaining.sort(key=lambda c: instance.d(0, c), reverse=True)

    max_routes = min(instance.k, 16)
    max_positions = 24
    for customer in remaining:
        best_move: tuple[tuple[tuple[float, ...], float], float, int, int] | None = None
        candidate_routes = set(nsmallest(max_routes, range(instance.k), key=lambda idx: sol.route_lengths[idx]))
        # Also try routes containing nearest assigned customers.
        for near in instance.nearest_customers(customer, 16):
            loc = sol.customer_pos[near]
            if loc is not None:
                candidate_routes.add(loc[0])
                if len(candidate_routes) >= max_routes:
                    break
        for r_idx in candidate_routes:
            route = sol.routes[r_idx]
            if len(route) <= max_positions + 1:
                positions = range(1, len(route) + 1)
            else:
                # Endpoints plus positions around closest nodes in this route.
                closest = nsmallest(max_positions // 2, range(1, len(route)), key=lambda p: instance.distance[customer][route[p]])
                pos_set = {1, len(route)}
                for p in closest:
                    pos_set.add(p)
                    pos_set.add(p + 1)
                positions = sorted(p for p in pos_set if 1 <= p <= len(route))
            for pos in positions:
                delta = sol.insertion_delta(r_idx, pos, customer)
                obj = sol.objective_after_delta(r_idx, delta)
                item = (obj, delta, r_idx, pos)
                if best_move is None or item[:2] < best_move[:2]:
                    best_move = item
        assert best_move is not None
        _, _, r_idx, pos = best_move
        sol.insert_customer(r_idx, pos, customer)

    return sol


def round_robin_nearest(instance: Instance, rng: random.Random | None = None) -> Solution:
    """Simpler fallback constructor: distribute customers by nearest extension."""
    rng = rng or random.Random()
    customers = set(range(1, instance.n + 1))
    routes = [[0] for _ in range(instance.k)]
    sol = Solution(instance, routes)

    for r_idx in range(min(instance.k, instance.n)):
        customer = max(customers, key=lambda c: instance.d(0, c))
        sol.insert_customer(r_idx, 1, customer)
        customers.remove(customer)

    while customers:
        r_idx = min(range(instance.k), key=lambda idx: sol.route_lengths[idx])
        tail = sol.routes[r_idx][-1]
        customer = min(customers, key=lambda c: instance.d(tail, c))
        sol.insert_customer(r_idx, len(sol.routes[r_idx]), customer)
        customers.remove(customer)

    return sol

