import random
from dataclasses import dataclass

from ...models import Distance, Instance, Solution
from .operators_utils import insertion_delta

InsertionScore = tuple[Distance, Distance, Distance]
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
        other_max = _max_route_length_except(lengths, r_idx)
        for pos in range(1, len(route) + 1):
            delta = insertion_delta(route, point, pos, instance)
            new_len = old_len + delta
            new_max = max(other_max, new_len)
            new_total = total + delta
            weighted = alpha * new_max + beta * delta
            score = (weighted, new_max, new_total)
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
        while unassigned:
            lengths = solution.route_lengths(instance)
            total = sum(lengths)
            selected_point = None
            selected_choice = None
            best_regret_score = None
            for point in unassigned:
                choices = []
                for r_idx, route in enumerate(solution.routes):
                    other_max = _max_route_length_except(lengths, r_idx)
                    for pos in range(1, len(route) + 1):
                        delta = insertion_delta(route, point, pos, instance)
                        new_len = lengths[r_idx] + delta
                        new_max = max(other_max, new_len)
                        new_total = total + delta
                        choices.append(((new_max, new_total, delta), r_idx, pos, delta))
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
                score = (regret, secondary, -best[0][0], -best[0][1])
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
    """Weighted repair emphasizing min-max first, insertion cost second."""

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


def _max_route_length_except(lengths: list[Distance], skipped_route: int) -> Distance:
    best = 0.0
    for route_index, length in enumerate(lengths):
        if route_index != skipped_route and length > best:
            best = length
    return best


def _choice_score(choice):
    return choice[0]


def _insertion_score_is_better(candidate_score, best_score) -> bool:
    if candidate_score[0] != best_score[0]:
        return candidate_score[0] < best_score[0]
    if candidate_score[1] != best_score[1]:
        return candidate_score[1] < best_score[1]
    return candidate_score[2] < best_score[2]


def _regret_score_is_better(candidate_score, best_score) -> bool:
    if candidate_score[0] != best_score[0]:
        return candidate_score[0] > best_score[0]
    if candidate_score[1] != best_score[1]:
        return candidate_score[1] > best_score[1]
    if candidate_score[2] != best_score[2]:
        return candidate_score[2] > best_score[2]
    return candidate_score[3] > best_score[3]


def default_repair_operators() -> list:
    return [GreedyMinMaxInsertion(), RegretInsertion(k=2), BalancedInsertion()]
