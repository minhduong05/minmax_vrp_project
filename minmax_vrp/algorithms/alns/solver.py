import random
import time
from dataclasses import dataclass

from .acceptance import SimulatedAnnealingAcceptance
from .adaptive import AdaptiveSelector
from .construction import build_greedy_balanced
from .destroy import default_destroy_operators
from ...models import Distance, Instance, Solution, better
from .repair import default_repair_operators


@dataclass
class ALNSConfig:
    time_limit: float = 10.0
    seed: int = 99
    q_min_ratio: float = 0.05
    q_max_ratio: float = 0.20
    reaction: float = 0.20
    segment_length: int = 50
    include_return_to_depot: bool = True

    reward_global_best: float = 10.0
    reward_current_improved: float = 5.0
    reward_accepted: float = 1.0
    reward_rejected: float = 0.0


@dataclass
class ALNSResult:
    best: Solution
    iterations: int
    runtime: float
    best_objective: tuple[Distance, Distance, Distance]
    destroy_weights: dict[str, float]
    repair_weights: dict[str, float]


class ALNSSolver:
    """Adaptive Large Neighborhood Search for Min-Max Vehicle Routing."""

    def __init__(
        self,
        config=None,
        destroy_operators=None,
        repair_operators=None,
    ) -> None:
        self.config = config or ALNSConfig()
        self.rng = random.Random(self.config.seed)
        self.destroy_selector = AdaptiveSelector(
            destroy_operators or default_destroy_operators(), reaction=self.config.reaction
        )
        self.repair_selector = AdaptiveSelector(
            repair_operators or default_repair_operators(), reaction=self.config.reaction
        )
        self.acceptance = SimulatedAnnealingAcceptance()

    def solve(self, instance: Instance, initial=None) -> ALNSResult:
        start = time.perf_counter()
        deadline = start + self.config.time_limit
        current = initial or build_greedy_balanced(
            instance,
            include_return_to_depot=self.config.include_return_to_depot,
            seed=self.config.seed,
        )
        current.assert_feasible(instance)
        best_sol = current.copy()
        self.acceptance.reset(best_sol.evaluate(instance).max_route_length)

        q_min = max(1, min(instance.n, int(self.config.q_min_ratio * instance.n)))
        q_max = max(q_min, min(instance.n, int(self.config.q_max_ratio * instance.n)))
        iterations = 0

        while time.perf_counter() < deadline:
            iterations += 1
            destroy_op = self.destroy_selector.choose(self.rng)
            repair_op = self.repair_selector.choose(self.rng)
            q = self.rng.randint(q_min, q_max) if instance.n > 0 else 0

            partial, removed = destroy_op(current, instance, q, self.rng)
            if not removed:
                continue
            candidate = repair_op(partial, removed, instance, self.rng)

            if not candidate.is_feasible(instance):
                reward = self.config.reward_rejected
            else:
                old_current = current
                accepted = self.acceptance.accept(current, candidate, instance, self.rng)
                if accepted:
                    current = candidate

                if better(candidate, best_sol, instance):
                    best_sol = candidate.copy()
                    reward = self.config.reward_global_best
                elif better(candidate, old_current, instance):
                    reward = self.config.reward_current_improved
                elif accepted:
                    reward = self.config.reward_accepted
                else:
                    reward = self.config.reward_rejected

            self.destroy_selector.record(destroy_op, reward)
            self.repair_selector.record(repair_op, reward)

            if iterations % self.config.segment_length == 0:
                self.destroy_selector.update_weights()
                self.repair_selector.update_weights()

        # Flush last segment scores.
        self.destroy_selector.update_weights()
        self.repair_selector.update_weights()
        runtime = time.perf_counter() - start
        return ALNSResult(
            best=best_sol,
            iterations=iterations,
            runtime=runtime,
            best_objective=best_sol.evaluate(instance).as_tuple(),
            destroy_weights=self.destroy_selector.weights_snapshot(),
            repair_weights=self.repair_selector.weights_snapshot(),
        )
