from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ...models import Instance, Solution, better


@dataclass
class SimulatedAnnealingAcceptance:
    """Compatibility facade for the project-level ALNS acceptance API."""

    initial_temperature: float = 300.0
    cooling_rate: float = 0.999

    def __post_init__(self) -> None:
        if self.initial_temperature < 0.0:
            raise ValueError("initial_temperature must be non-negative")
        if not 0.0 < self.cooling_rate <= 1.0:
            raise ValueError("cooling_rate must be in (0, 1]")
        self.temperature = self.initial_temperature

    def reset(self, objective_scale: float | None = None) -> None:
        del objective_scale
        self.temperature = self.initial_temperature

    def scalar_value(self, solution: Solution, instance: Instance) -> float:
        evaluation = solution.evaluate(instance)
        return evaluation.max_route_length * 1_000_000.0 + evaluation.total_distance

    def accept(
        self,
        current: Solution,
        candidate: Solution,
        instance: Instance,
        rng: random.Random,
    ) -> bool:
        if better(candidate, current, instance):
            self.temperature *= self.cooling_rate
            return True
        if self.temperature <= 0.0:
            self.temperature *= self.cooling_rate
            return False
        delta = self.scalar_value(candidate, instance) - self.scalar_value(current, instance)
        probability = math.exp(-delta / max(self.temperature, 1e-12))
        accepted = rng.random() < probability
        self.temperature *= self.cooling_rate
        return accepted
