import random
import time
from dataclasses import dataclass

from .acceptance import SimulatedAnnealingAcceptance
from .adaptive import AdaptiveSelector
from .construction import build_greedy_balanced
from .destroy import default_destroy_operators
from ..route_constraints import has_positive_route_lengths
from ...models import Distance, Instance, Solution, better
from .repair import default_repair_operators


@dataclass
class ALNSConfig:
    time_limit: float = 10.0
    seed: int = 99
    q_min_ratio: float = 0.02
    q_max_ratio: float = 0.10
    initial_temperature: float = 300.0
    cooling_rate: float = 0.999
    reaction: float = 0.20
    segment_length: int = 50
    require_positive_route_lengths: bool = True

    reward_global_best: float = 10.0
    reward_current_improved: float = 5.0
    reward_accepted: float = 2.0
    reward_rejected: float = 0.0

    def __post_init__(self) -> None:
        if self.time_limit < 0.0:
            raise ValueError("time_limit must be non-negative")
        if self.q_min_ratio < 0.0:
            raise ValueError("q_min_ratio must be non-negative")
        if self.q_max_ratio < self.q_min_ratio:
            raise ValueError("q_max_ratio must be greater than or equal to q_min_ratio")
        if self.initial_temperature < 0.0:
            raise ValueError("initial_temperature must be non-negative")
        if not 0.0 < self.cooling_rate <= 1.0:
            raise ValueError("cooling_rate must be in (0, 1]")
        if not 0.0 <= self.reaction <= 1.0:
            raise ValueError("reaction must be in [0, 1]")
        if self.segment_length <= 0:
            raise ValueError("segment_length must be positive")
        rewards = [
            self.reward_global_best,
            self.reward_current_improved,
            self.reward_accepted,
            self.reward_rejected,
        ]
        if any(reward < 0.0 for reward in rewards):
            raise ValueError("ALNS rewards must be non-negative")


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
        self.acceptance = SimulatedAnnealingAcceptance(
            initial_temperature=self.config.initial_temperature,
            cooling_rate=self.config.cooling_rate,
        )

    def solve(self, instance: Instance, initial=None) -> ALNSResult:
        start = time.perf_counter()
        deadline = start + self.config.time_limit
        current = initial or build_greedy_balanced(
            instance,
            seed=self.config.seed,
        )
        current.assert_feasible(instance)
        if self.config.require_positive_route_lengths and not has_positive_route_lengths(
            current, instance
        ):
            raise ValueError(
                "ALNS requires every vehicle to have a positive-length route; "
                f"got n={instance.n}, k={instance.k}"
            )
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

            if not self._candidate_is_valid(candidate, instance):
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

    def _candidate_is_valid(self, candidate: Solution, instance: Instance) -> bool:
        if not candidate.is_feasible(instance):
            return False
        if self.config.require_positive_route_lengths:
            return has_positive_route_lengths(candidate, instance)
        return True
