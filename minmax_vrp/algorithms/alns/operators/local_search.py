from __future__ import annotations

import random
from heapq import nsmallest

from minmax_vrp.algorithms.alns.core.solution import Solution
from minmax_vrp.algorithms.alns.operators.insertion import _positions_for_route, _route_subset


def improve_by_relocate(solution: Solution, max_checks: int = 5000, rng: random.Random | None = None) -> Solution:
    """Sampled first-improvement relocate local search.

    Optimized version: it no longer deep-copies the whole solution for every
    tested move. A customer is temporarily removed, candidate insertions are
    evaluated by delta, and the move is either applied or reverted.
    """
    rng = rng or random.Random()
    sol = solution.copy()
    checks = 0

    while checks < max_checks:
        positions = list(sol.iter_customers())
        if not positions:
            break
        rng.shuffle(positions)
        improved = False
        base_obj = sol.objective()

        for from_r, from_pos, customer in positions[: min(len(positions), 200)]:
            loc = sol.customer_pos[customer]
            if loc is None:
                continue
            from_r, from_pos = loc

            removed_customer = sol.remove_at(from_r, from_pos, add_to_unassigned=False)
            assert removed_customer == customer

            best: tuple[tuple[tuple[float, ...], float], int, int] | None = None
            route_indices = set(_route_subset(sol, customer, max_routes=12))
            route_indices.update(nsmallest(max(1, sol.instance.k // 5), range(sol.instance.k), key=lambda idx: sol.route_lengths[idx]))

            for to_r in route_indices:
                for to_pos in _positions_for_route(sol, to_r, customer, max_positions=18):
                    delta = sol.insertion_delta(to_r, to_pos, customer)
                    obj = sol.objective_after_delta(to_r, delta)
                    item = (obj, to_r, to_pos)
                    if best is None or item < best:
                        best = item
                    checks += 1
                    if checks >= max_checks:
                        break
                if checks >= max_checks:
                    break

            if best and best[0] < base_obj:
                _, to_r, to_pos = best
                sol.insert_customer(to_r, to_pos, customer)
                improved = True
                break

            # Revert to the original route and position if no improving move was used.
            sol.insert_customer(from_r, from_pos, customer)

            if checks >= max_checks:
                break

        if not improved:
            break

    return sol

