import math
import random
from dataclasses import dataclass

from ...models import Distance, Instance, Solution


@dataclass
class SimulatedAnnealingAcceptance:
    """Accept improving moves, and sometimes accept worsening moves.

    The value used is the lexicographic objective converted to a scalar by giving
    max_route_length a very large priority over total_distance.
    """

    initial_temperature: float = 1000.0
    cooling_rate: float = 0.999
    min_temperature: float = 1e-6
    total_weight: float = 1e-6
    temperature: float = 1000.0

    def reset(self, initial_objective: Distance) -> None:
        self.temperature = max(self.initial_temperature, 0.05 * max(1, initial_objective))

    def scalar_value(self, solution: Solution, instance: Instance) -> float:
        ev = solution.evaluate(instance)
        # max route dominates, total distance breaks ties softly.
        return ev.max_route_length + self.total_weight * ev.total_distance

    def accept(self, current: Solution, candidate: Solution, instance: Instance, rng: random.Random) -> bool:
        cur = self.scalar_value(current, instance)
        new = self.scalar_value(candidate, instance)
        if new <= cur:
            accepted = True
        else:
            probability = math.exp(-(new - cur) / max(self.temperature, self.min_temperature))
            accepted = rng.random() < probability
        self.temperature = max(self.min_temperature, self.temperature * self.cooling_rate)
        return accepted
