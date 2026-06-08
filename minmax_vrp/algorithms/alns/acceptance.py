import math
import random
from dataclasses import dataclass

from ...models import Distance, Evaluation, Instance, Solution


@dataclass
class SimulatedAnnealingAcceptance:
    """Accept improving moves, and sometimes accept worsening moves.

    The search objective is lexicographic: first max route, then balance, then
    total distance. Therefore every lexicographically non-worse move is
    accepted deterministically. Simulated annealing is used only for genuinely
    worse moves, using the first worsening objective component as the
    deterioration amount.
    """

    initial_temperature: float = 1000.0
    cooling_rate: float = 0.999
    min_temperature: float = 1e-6
    total_weight: float = 1e-6
    balance_weight: float = 1.0
    temperature: float = 1000.0

    def reset(self, initial_objective: Distance) -> None:
        self.temperature = max(self.initial_temperature, 0.05 * max(1, initial_objective))

    def scalar_value(self, solution: Solution, instance: Instance) -> float:
        ev = solution.evaluate(instance)
        # Diagnostic scalar only; accept() uses lexicographic comparison first.
        return ev.max_route_length + self.total_weight * ev.total_distance

    def deterioration(self, current: Evaluation, candidate: Evaluation) -> Distance:
        """Return a positive SA cost for a lexicographically worse candidate."""
        cur = current.rank_tuple()
        new = candidate.rank_tuple()
        if new <= cur:
            return 0.0

        if candidate.max_route_length != current.max_route_length:
            return candidate.max_route_length - current.max_route_length
        if candidate.balance != current.balance:
            return self.balance_weight * (candidate.balance - current.balance)
        return self.total_weight * (candidate.total_distance - current.total_distance)

    def accept(
        self,
        current: Solution,
        candidate: Solution,
        instance: Instance,
        rng: random.Random,
    ) -> bool:
        cur_eval = current.evaluate(instance)
        new_eval = candidate.evaluate(instance)
        deterioration = self.deterioration(cur_eval, new_eval)
        if deterioration <= 0.0:
            accepted = True
        else:
            probability = math.exp(-deterioration / max(self.temperature, self.min_temperature))
            accepted = rng.random() < probability
        self.temperature = max(self.min_temperature, self.temperature * self.cooling_rate)
        return accepted
