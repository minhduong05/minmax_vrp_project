from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Iterable

from .instance import Instance

Objective = tuple[tuple[float, ...], float]
CustomerPosition = tuple[int, int] | None


def objective_from_lengths(lengths: list[float]) -> Objective:
    return (tuple(sorted(lengths, reverse=True)), sum(lengths))


@dataclass
class Solution:
    """Mutable ALNS state for Min-Max VRP.

    Fast-path choices:
    - route lengths are cached;
    - insert/remove are evaluated by O(1) distance deltas;
    - customer_pos[c] gives the current route/position of customer c, so destroy
      operators do not scan all routes when removing selected customers.
    """

    instance: Instance
    routes: list[list[int]]
    route_lengths: list[float] = field(default_factory=list)
    unassigned: list[int] = field(default_factory=list)
    customer_pos: list[CustomerPosition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.routes) != self.instance.k:
            raise ValueError(f"Expected {self.instance.k} routes, got {len(self.routes)}.")
        for r in self.routes:
            if not r or r[0] != 0:
                raise ValueError("Every route must start with depot 0.")
        if not self.route_lengths:
            self.route_lengths = [self.compute_route_length(r) for r in self.routes]
        if not self.customer_pos:
            self.rebuild_customer_positions()

    def rebuild_customer_positions(self) -> None:
        self.customer_pos = [None] * (self.instance.n + 1)
        for r_idx, route in enumerate(self.routes):
            for pos, customer in enumerate(route[1:], start=1):
                self.customer_pos[customer] = (r_idx, pos)
        for customer in self.unassigned:
            if 0 <= customer <= self.instance.n:
                self.customer_pos[customer] = None

    def copy(self) -> "Solution":
        return Solution(
            self.instance,
            [r[:] for r in self.routes],
            self.route_lengths[:],
            self.unassigned[:],
            self.customer_pos[:],
        )

    def objective(self) -> Objective:
        return objective_from_lengths(self.route_lengths)

    def objective_after_delta(self, route_idx: int, delta: float) -> Objective:
        new_lengths = self.route_lengths[:]
        new_lengths[route_idx] += delta
        return objective_from_lengths(new_lengths)

    def max_route_length(self) -> float:
        return max(self.route_lengths) if self.route_lengths else 0.0

    def total_distance(self) -> float:
        return sum(self.route_lengths)

    def balance(self) -> float:
        return max(self.route_lengths) - min(self.route_lengths) if self.route_lengths else 0.0

    def compute_route_length(self, route: list[int]) -> float:
        if len(route) <= 1:
            return 0.0
        total = sum(self.instance.d(a, b) for a, b in zip(route, route[1:]))
        if self.instance.return_to_depot:
            total += self.instance.d(route[-1], 0)
        return total

    def insertion_delta(self, route_idx: int, pos: int, customer: int) -> float:
        route = self.routes[route_idx]
        prev_node = route[pos - 1]
        next_node = route[pos] if pos < len(route) else (0 if self.instance.return_to_depot else None)
        if next_node is None:
            return self.instance.d(prev_node, customer)
        return self.instance.d(prev_node, customer) + self.instance.d(customer, next_node) - self.instance.d(prev_node, next_node)

    def removal_delta(self, route_idx: int, pos: int) -> float:
        route = self.routes[route_idx]
        if pos <= 0 or pos >= len(route):
            raise ValueError("Cannot remove depot or invalid position.")
        prev_node = route[pos - 1]
        customer = route[pos]
        next_node = route[pos + 1] if pos + 1 < len(route) else (0 if self.instance.return_to_depot else None)
        if next_node is None:
            return -self.instance.d(prev_node, customer)
        return self.instance.d(prev_node, next_node) - self.instance.d(prev_node, customer) - self.instance.d(customer, next_node)

    def _refresh_positions_from(self, route_idx: int, start_pos: int) -> None:
        route = self.routes[route_idx]
        for pos in range(max(1, start_pos), len(route)):
            self.customer_pos[route[pos]] = (route_idx, pos)

    def insert_customer(self, route_idx: int, pos: int, customer: int) -> None:
        delta = self.insertion_delta(route_idx, pos, customer)
        self.routes[route_idx].insert(pos, customer)
        self.route_lengths[route_idx] += delta
        self._refresh_positions_from(route_idx, pos)

    def remove_at(self, route_idx: int, pos: int, add_to_unassigned: bool = True) -> int:
        delta = self.removal_delta(route_idx, pos)
        customer = self.routes[route_idx].pop(pos)
        self.route_lengths[route_idx] += delta
        self.customer_pos[customer] = None
        self._refresh_positions_from(route_idx, pos)
        if add_to_unassigned:
            self.unassigned.append(customer)
        return customer

    def remove_customer(self, customer: int, add_to_unassigned: bool = True) -> bool:
        if customer < 0 or customer > self.instance.n:
            return False
        loc = self.customer_pos[customer]
        if loc is None:
            return False
        r_idx, pos = loc
        if pos >= len(self.routes[r_idx]) or self.routes[r_idx][pos] != customer:
            self.rebuild_customer_positions()
            loc = self.customer_pos[customer]
            if loc is None:
                return False
            r_idx, pos = loc
        self.remove_at(r_idx, pos, add_to_unassigned)
        return True

    def iter_customers(self) -> Iterable[tuple[int, int, int]]:
        for r_idx, route in enumerate(self.routes):
            for pos in range(1, len(route)):
                yield r_idx, pos, route[pos]

    def validate(self, strict_use_all_routes: bool = True) -> None:
        seen: list[int] = []
        for route in self.routes:
            if not route or route[0] != 0:
                raise ValueError("Invalid route: every route must start with 0.")
            seen.extend(route[1:])
        assigned = set(seen)
        if len(seen) != len(assigned):
            raise ValueError("A customer is visited more than once.")
        expected = set(range(1, self.instance.n + 1))
        if assigned | set(self.unassigned) != expected:
            missing = expected - (assigned | set(self.unassigned))
            extra = (assigned | set(self.unassigned)) - expected
            raise ValueError(f"Invalid customer set. Missing={missing}, extra={extra}")
        if strict_use_all_routes and any(len(r) <= 1 for r in self.routes):
            raise ValueError("At least one route is empty, but strict_use_all_routes=True.")
        for idx, route in enumerate(self.routes):
            length = self.compute_route_length(route)
            if not isclose(length, self.route_lengths[idx], rel_tol=1e-8, abs_tol=1e-8):
                raise ValueError(f"Cached route length mismatch at route {idx}: {self.route_lengths[idx]} vs {length}")
        for customer in assigned:
            loc = self.customer_pos[customer]
            if loc is None:
                raise ValueError(f"Missing cached position for customer {customer}.")
            r_idx, pos = loc
            if self.routes[r_idx][pos] != customer:
                raise ValueError(f"Wrong cached position for customer {customer}.")

    def to_output_text(self) -> str:
        lines = [str(self.instance.k)]
        for route in self.routes:
            lines.append(str(len(route)))
            lines.append(" ".join(str(x) for x in route))
        return "\n".join(lines) + "\n"


def better(a: Solution, b: Solution) -> bool:
    return a.objective() < b.objective()

