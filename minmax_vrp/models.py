from dataclasses import dataclass

Distance = float


@dataclass(frozen=True)
class Instance:
    """Input data for Min-Max Vehicle Routing.

    Nodes are indexed from 0..n. Node 0 is the depot. Pickup points are 1..n.
    The project output format uses K routes; every route starts with 0 and then
    lists pickup points. Returning to depot is configurable because some VRP
    variants require it, while the provided mini-project statement only fixes
    x[1] = 0 for each route.
    """

    n: int
    k: int
    distance: list[list[Distance]]

    def __post_init__(self) -> None:
        if self.n < 0:
            raise ValueError("n must be non-negative")
        if self.k <= 0:
            raise ValueError("k must be positive")
        expected = self.n + 1
        if len(self.distance) != expected:
            raise ValueError(f"distance matrix must have {expected} rows")
        for row in self.distance:
            if len(row) != expected:
                raise ValueError(f"distance matrix must be {expected} x {expected}")

    @property
    def pickup_points(self) -> range:
        return range(1, self.n + 1)


@dataclass
class Evaluation:
    max_route_length: Distance
    total_distance: Distance
    balance: Distance

    def as_tuple(self) -> tuple[Distance, Distance, Distance]:
        """Lexicographic objective: first minimize max route, then total, then balance."""
        return (self.max_route_length, self.total_distance, self.balance)


@dataclass
class Solution:
    """A feasible or partial routing solution.

    routes[k] is a list like [0, pickup_point_a, pickup_point_b, ...].
    """

    routes: list[list[int]]
    include_return_to_depot: bool = True

    def copy(self) -> "Solution":
        copied_routes = []
        for route in self.routes:
            copied_routes.append(route[:])
        return Solution(copied_routes, self.include_return_to_depot)

    def all_pickup_points(self) -> list[int]:
        points = []
        for route in self.routes:
            for node in route:
                if node != 0:
                    points.append(node)
        return points

    def route_length(self, route: list[int], d: list[list[Distance]]) -> Distance:
        if len(route) <= 1:
            return 0.0
        length = 0.0
        for i in range(len(route) - 1):
            length += d[route[i]][route[i + 1]]
        if self.include_return_to_depot:
            length += d[route[-1]][0]
        return length

    def route_lengths(self, instance: Instance) -> list[Distance]:
        lengths = []
        for route in self.routes:
            lengths.append(self.route_length(route, instance.distance))
        return lengths

    def evaluate(self, instance: Instance) -> Evaluation:
        lengths = self.route_lengths(instance)
        max_len = max(lengths) if lengths else 0
        total = sum(lengths)
        balance = max_len - min(lengths) if lengths else 0
        return Evaluation(max_len, total, balance)

    def is_feasible(self, instance: Instance) -> bool:
        if len(self.routes) != instance.k:
            return False
        seen = [False] * (instance.n + 1)
        for route in self.routes:
            if not route or route[0] != 0:
                return False
            for node in route[1:]:
                if node < 1 or node > instance.n:
                    return False
                if seen[node]:
                    return False
                seen[node] = True

        for point in instance.pickup_points:
            if not seen[point]:
                return False
        return True

    def assert_feasible(self, instance: Instance) -> None:
        if not self.is_feasible(instance):
            raise ValueError("solution is not feasible for the instance")


def better(a: Solution, b: Solution, instance: Instance) -> bool:
    """Return True if a is better than b under lexicographic min-max objective."""
    eval_a = a.evaluate(instance)
    eval_b = b.evaluate(instance)

    if eval_a.max_route_length != eval_b.max_route_length:
        return eval_a.max_route_length < eval_b.max_route_length
    if eval_a.total_distance != eval_b.total_distance:
        return eval_a.total_distance < eval_b.total_distance
    return eval_a.balance < eval_b.balance
