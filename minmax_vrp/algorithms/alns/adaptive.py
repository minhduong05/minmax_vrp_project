import random
from dataclasses import dataclass


@dataclass
class OperatorStats:
    weight: float = 1.0
    score: float = 0.0
    uses: int = 0


class AdaptiveSelector:
    """Roulette-wheel operator selector with segmented ALNS weight updates."""

    def __init__(self, operators: list, reaction: float = 0.2, min_weight: float = 0.05) -> None:
        if not operators:
            raise ValueError("at least one operator is required")

        self.operators = operators
        self.reaction = reaction
        self.min_weight = min_weight
        self.stats: dict[str, OperatorStats] = {}

        for operator in operators:
            self.stats[operator.name] = OperatorStats()

    def choose(self, rng: random.Random):
        total_weight = 0.0
        for operator in self.operators:
            total_weight += self.stats[operator.name].weight

        threshold = rng.random() * total_weight
        accumulated_weight = 0.0
        for operator in self.operators:
            accumulated_weight += self.stats[operator.name].weight
            if accumulated_weight >= threshold:
                return operator

        return self.operators[-1]

    def record(self, operator, reward: float) -> None:
        stat = self.stats[operator.name]
        stat.score += reward
        stat.uses += 1

    def update_weights(self) -> None:
        for stat in self.stats.values():
            if stat.uses > 0:
                average_score = stat.score / stat.uses
                new_weight = (1.0 - self.reaction) * stat.weight + self.reaction * average_score
                stat.weight = max(self.min_weight, new_weight)

            stat.score = 0.0
            stat.uses = 0

    def weights_snapshot(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for name, stat in self.stats.items():
            weights[name] = stat.weight
        return weights
