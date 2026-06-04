import random

from ...models import Distance, Instance, Solution
from .operators_utils import insertion_delta


def build_round_robin(instance: Instance, include_return_to_depot: bool = True) -> Solution:
    routes = []
    for _ in range(instance.k):
        routes.append([0])
    for idx, point in enumerate(instance.pickup_points):
        routes[idx % instance.k].append(point)
    return Solution(routes, include_return_to_depot)


def build_greedy_balanced(
    instance: Instance,
    include_return_to_depot: bool = True,
    seed=None,
) -> Solution:
    """Construct a solution by minimizing the current min-max objective after each insertion.

    This is intentionally aligned with the mini-project objective: reduce the longest route,
    not merely the total distance.
    """
    rng = random.Random(seed)
    points = list(instance.pickup_points)
    rng.shuffle(points)

    routes = []
    lengths = []
    for _ in range(instance.k):
        routes.append([0])
        lengths.append(0)

    # Seed up to K routes with one pickup point nearest to depot to avoid too many empty routes.
    def distance_from_depot(point: int) -> Distance:
        return instance.distance[0][point]

    points.sort(key=distance_from_depot)
    for r_idx in range(min(instance.k, len(points))):
        point = points.pop(0)
        routes[r_idx].append(point)
        lengths[r_idx] = Solution([routes[r_idx]], include_return_to_depot).route_length(
            routes[r_idx], instance.distance
        )

    # The full "best point among all remaining points" variant is O(N^3) on large
    # instances.  For N up to 1000, insert points one-by-one but still evaluate every
    # route/position for the chosen point.  This keeps construction fast enough that
    # ALNS gets most of the time budget.
    rng.shuffle(points)
    running_total = sum(lengths)
    for point in points:
        best_choice = None
        for r_idx, route in enumerate(routes):
            old_length = lengths[r_idx]
            other_max = 0
            for other_route, other_length in enumerate(lengths):
                if other_route != r_idx and other_length > other_max:
                    other_max = other_length
            for pos in range(1, len(route) + 1):
                delta = insertion_delta(route, point, pos, instance, include_return_to_depot)
                new_length = old_length + delta
                new_max = max(other_max, new_length)
                new_total = running_total + delta
                score = (new_max, new_total, new_length)
                if best_choice is None or _insertion_score_is_better(score, best_choice[0]):
                    best_choice = (score, r_idx, pos, delta)
        assert best_choice is not None
        _, r_idx, pos, delta = best_choice
        delta = insertion_delta(routes[r_idx], point, pos, instance, include_return_to_depot)
        routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta
        running_total += delta

    return Solution(routes, include_return_to_depot)


def _insertion_score_is_better(
    candidate_score: tuple[Distance, Distance, Distance],
    best_score: tuple[Distance, Distance, Distance],
) -> bool:
    if candidate_score[0] != best_score[0]:
        return candidate_score[0] < best_score[0]
    if candidate_score[1] != best_score[1]:
        return candidate_score[1] < best_score[1]
    return candidate_score[2] < best_score[2]
