import random
from dataclasses import dataclass

from ...models import Distance, Instance, Solution
from .operators_utils import insertion_delta

InsertionScore = tuple[Distance, Distance, Distance, Distance]
InsertionChoice = tuple[InsertionScore, int, int, Distance]


def _best_insertion_for_point(
    solution: Solution,
    point: int,
    instance: Instance,
    alpha: float = 1.0,
    beta: float = 0.0,
) -> InsertionChoice:
    """Return score, route index, insertion position, delta."""
    lengths = solution.route_lengths(instance)
    total = sum(lengths)
    return _best_insertion_for_point_with_state(
        solution, point, instance, lengths, total, alpha=alpha, beta=beta
    )


def _best_insertion_for_point_with_state(
    solution: Solution,
    point: int,
    instance: Instance,
    lengths: list[Distance],
    total: Distance,
    alpha: float = 1.0,
    beta: float = 0.0,
) -> InsertionChoice:
    """Return best insertion using already computed route lengths."""
    best = None
    for r_idx, route in enumerate(solution.routes):
        old_len = lengths[r_idx]
        other_max, other_min = _route_length_extremes_except(lengths, r_idx)
        for pos in range(1, len(route) + 1):
            delta = insertion_delta(route, point, pos, instance)
            new_len = old_len + delta
            new_max = max(other_max, new_len)
            new_min = new_len if other_min is None else min(other_min, new_len)
            new_balance = new_max - new_min
            new_total = total + delta
            cost_tiebreak = alpha * new_total + beta * delta
            score = (new_max, new_balance, new_total, cost_tiebreak)
            if best is None or _insertion_score_is_better(score, best[0]):
                best = (score, r_idx, pos, delta)
    assert best is not None
    return best


@dataclass(frozen=True)
class GreedyMinMaxInsertion:
    name: str = "greedy_minmax_insertion"

    def __call__(
        self,
        partial: Solution,
        removed: list[int],
        instance: Instance,
        rng: random.Random,
    ) -> Solution:
        solution = partial.copy()
        unassigned = removed[:]
        rng.shuffle(unassigned)
        _activate_zero_length_routes(solution, unassigned, instance, rng)
        lengths = solution.route_lengths(instance)
        total = sum(lengths)
        while unassigned:
            best_choice = None
            for point in unassigned:
                choice = _best_insertion_for_point_with_state(
                    solution, point, instance, lengths, total
                )
                if best_choice is None or _insertion_score_is_better(
                    choice[0], best_choice[0]
                ):
                    score, r_idx, pos, delta = choice
                    best_choice = (score, r_idx, pos, delta, point)
            assert best_choice is not None
            _, r_idx, pos, delta, point = best_choice
            solution.routes[r_idx].insert(pos, point)
            lengths[r_idx] += delta
            total += delta
            unassigned.remove(point)
        return solution


@dataclass(frozen=True)
class RegretInsertion:
    k: int = 2
    name: str = "regret2_minmax_insertion"

    def __call__(
        self,
        partial: Solution,
        removed: list[int],
        instance: Instance,
        rng: random.Random,
    ) -> Solution:
        solution = partial.copy()
        unassigned = removed[:]
        rng.shuffle(unassigned)
        _activate_zero_length_routes(solution, unassigned, instance, rng)
        while unassigned:
            lengths = solution.route_lengths(instance)
            total = sum(lengths)
            selected_point = None
            selected_choice = None
            best_regret_score = None
            for point in unassigned:
                choices = []
                for r_idx, route in enumerate(solution.routes):
                    other_max, other_min = _route_length_extremes_except(lengths, r_idx)
                    for pos in range(1, len(route) + 1):
                        delta = insertion_delta(route, point, pos, instance)
                        new_len = lengths[r_idx] + delta
                        new_max = max(other_max, new_len)
                        new_min = new_len if other_min is None else min(other_min, new_len)
                        new_balance = new_max - new_min
                        new_total = total + delta
                        choices.append(
                            ((new_max, new_balance, new_total, delta), r_idx, pos, delta)
                        )
                choices.sort(key=_choice_score)
                best = choices[0]
                considered = choices[1 : min(self.k, len(choices))]
                if considered:
                    regret = 0
                    secondary = 0
                    for choice in considered:
                        regret += choice[0][0] - best[0][0]
                        secondary += choice[0][1] - best[0][1]
                else:
                    regret = 0
                    secondary = 0
                # Maximize regret, but if tied choose lower best insertion score.
                score = (regret, secondary, -best[0][0], -best[0][1], -best[0][2])
                if best_regret_score is None or _regret_score_is_better(
                    score, best_regret_score
                ):
                    best_regret_score = score
                    selected_point = point
                    selected_choice = best
            assert selected_point is not None and selected_choice is not None
            _, r_idx, pos, _delta = selected_choice
            solution.routes[r_idx].insert(pos, selected_point)
            unassigned.remove(selected_point)
        return solution


@dataclass(frozen=True)
class BalancedInsertion:
    """Repair emphasizing max route first, balance second, insertion cost third."""

    alpha: float = 0.85
    beta: float = 0.15
    name: str = "balanced_insertion"

    def __call__(
        self,
        partial: Solution,
        removed: list[int],
        instance: Instance,
        rng: random.Random,
    ) -> Solution:
        solution = partial.copy()
        unassigned = removed[:]
        rng.shuffle(unassigned)
        _activate_zero_length_routes(solution, unassigned, instance, rng)
        lengths = solution.route_lengths(instance)
        total = sum(lengths)
        while unassigned:
            best_choice = None
            for point in unassigned:
                choice = _best_insertion_for_point_with_state(
                    solution,
                    point,
                    instance,
                    lengths,
                    total,
                    alpha=self.alpha,
                    beta=self.beta,
                )
                if best_choice is None or _insertion_score_is_better(
                    choice[0], best_choice[0]
                ):
                    score, r_idx, pos, delta = choice
                    best_choice = (score, r_idx, pos, delta, point)
            assert best_choice is not None
            _, r_idx, pos, delta, point = best_choice
            solution.routes[r_idx].insert(pos, point)
            lengths[r_idx] += delta
            total += delta
            unassigned.remove(point)
        return solution


def _route_length_extremes_except(
    lengths: list[Distance], skipped_route: int
) -> tuple[Distance, Distance | None]:
    best_max = 0.0
    best_min = None
    for route_index, length in enumerate(lengths):
        if route_index == skipped_route:
            continue
        if length > best_max:
            best_max = length
        if best_min is None or length < best_min:
            best_min = length
    return best_max, best_min


def _activate_zero_length_routes(
    solution: Solution,
    unassigned: list[int],
    instance: Instance,
    rng: random.Random,
) -> None:
    """Give every zero-length route a pickup before normal repair continues."""
    inactive_routes = [
        route_index
        for route_index, route in enumerate(solution.routes)
        if solution.route_length(route, instance.distance) <= 0.0
    ]
    rng.shuffle(inactive_routes)

    for route_index in inactive_routes:
        if not unassigned:
            return
        route = solution.routes[route_index]
        old_length = solution.route_length(route, instance.distance)
        if old_length > 0.0:
            continue

        best_choice = None
        lengths = solution.route_lengths(instance)
        total = sum(lengths)
        other_max, other_min = _route_length_extremes_except(lengths, route_index)
        for point in unassigned:
            for pos in range(1, len(route) + 1):
                delta = insertion_delta(route, point, pos, instance)
                new_length = old_length + delta
                new_max = max(other_max, new_length)
                new_min = new_length if other_min is None else min(other_min, new_length)
                new_balance = new_max - new_min
                new_total = total + delta
                active_rank = 0 if new_length > 0.0 else 1
                score = (active_rank, new_max, new_balance, new_total, delta)
                if best_choice is None or score < best_choice[0]:
                    best_choice = (score, point, pos)

        assert best_choice is not None
        _, point, pos = best_choice
        route.insert(pos, point)
        unassigned.remove(point)


def _choice_score(choice):
    return choice[0]


def _insertion_score_is_better(candidate_score, best_score) -> bool:
    return candidate_score < best_score


def _regret_score_is_better(candidate_score, best_score) -> bool:
    return candidate_score > best_score


def default_repair_operators() -> list:
    return [GreedyMinMaxInsertion(), RegretInsertion(k=2), BalancedInsertion()]
