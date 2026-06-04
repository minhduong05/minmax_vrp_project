from ...models import Distance, Instance, Solution


def insertion_delta(
    route: list[int],
    point: int,
    position: int,
    instance: Instance,
    include_return_to_depot: bool,
) -> Distance:
    """Cost change when inserting a pickup point at route[position].

    position is in [1, len(route)] because position 0 is reserved for depot.
    """
    if position < 1 or position > len(route):
        raise ValueError("insertion position must be between 1 and len(route)")
    d = instance.distance  # matrix distance
    prev_node = route[position - 1]
    if position == len(route):
        if include_return_to_depot:
            return d[prev_node][point] + d[point][0] - d[prev_node][0]
        return d[prev_node][point]
    next_node = route[position]
    return d[prev_node][point] + d[point][next_node] - d[prev_node][next_node]


def removal_saving(
    route: list[int],
    position: int,
    instance: Instance,
    include_return_to_depot: bool,
) -> Distance:
    """Length decrease if route[position] is removed. Larger is better to remove."""
    if position <= 0 or position >= len(route):
        raise ValueError("removal position must point to a pickup point in the route")
    d = instance.distance
    node = route[position]
    prev_node = route[position - 1]
    if position == len(route) - 1:
        if include_return_to_depot:
            return d[prev_node][node] + d[node][0] - d[prev_node][0]
        return d[prev_node][node]
    next_node = route[position + 1]
    return d[prev_node][node] + d[node][next_node] - d[prev_node][next_node]


def remove_pickup_point(solution: Solution, point: int) -> bool:
    """Remove pickup point from solution. Return True if found."""
    for route in solution.routes:
        for pos in range(1, len(route)):
            if route[pos] == point:
                route.pop(pos)
                return True
    return False
