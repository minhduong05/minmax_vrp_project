from __future__ import annotations

import math
import random
from dataclasses import dataclass

from minmax_vrp.algorithms.alns.core.solution import Solution


def scalar_objective(solution: Solution) -> float:
    """Scalar value for probabilistic acceptance.

    True comparison in the solver is still lexicographic. SA only needs a stable
    numerical delta, so we approximate the lexicographic objective by weighting
    the longest routes more heavily than later routes, and then adding a small
    total-distance tie-breaker.
    """
    sorted_lengths = sorted(solution.route_lengths, reverse=True)
    value = 0.0
    weight = 1.0
    for length in sorted_lengths[: min(10, len(sorted_lengths))]:
        value += weight * length
        weight *= 0.1
    value += 1e-6 * solution.total_distance()
    return value


@dataclass
class SimulatedAnnealing:
    start_temperature: float
    end_temperature: float = 1e-3
    cooling_rate: float = 0.9995

    def __post_init__(self) -> None:
        self.temperature = max(self.start_temperature, self.end_temperature)

    @classmethod
    def auto_fit(
        cls,
        initial: Solution,
        worse_accept_prob: float = 0.8,
        worse_fraction: float = 0.05,
        iterations: int = 10000,
    ) -> "SimulatedAnnealing":
        base = max(1.0, scalar_objective(initial))
        worse_delta = base * worse_fraction
        temp = -worse_delta / math.log(worse_accept_prob)
        cooling = (1e-3 / temp) ** (1 / max(1, iterations)) if temp > 1e-3 else 0.9995
        return cls(temp, 1e-3, cooling)

    def accept(self, current: Solution, candidate: Solution, rng: random.Random) -> bool:
        if candidate.objective() <= current.objective():
            return True
        delta = scalar_objective(candidate) - scalar_objective(current)
        # The scalar is only an approximation of the lexicographic objective. If
        # it says the candidate is not worse, accepting it is reasonable.
        if delta <= 0:
            return True
        exponent = -delta / max(self.temperature, self.end_temperature)
        if exponent < -745:  # exp(-745) is close to the smallest useful float.
            return False
        prob = math.exp(exponent)
        return rng.random() < prob

    def step(self) -> None:
        self.temperature = max(self.end_temperature, self.temperature * self.cooling_rate)


@dataclass
class HillClimbing:
    def accept(self, current: Solution, candidate: Solution, rng: random.Random) -> bool:
        return candidate.objective() <= current.objective()

    def step(self) -> None:
        return None

