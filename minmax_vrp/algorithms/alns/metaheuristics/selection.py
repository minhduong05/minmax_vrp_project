from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

from minmax_vrp.algorithms.alns.core.solution import Solution

T = TypeVar("T")
Operator = Callable[[Solution, random.Random], Solution]


@dataclass
class AdaptiveRouletteWheel(Generic[T]):
    """Adaptive operator selection similar to classical ALNS.

    Weights are used to sample operators. Scores are accumulated during a segment;
    at segment end, weights are smoothed toward average observed score.
    """

    operators: list[T]
    reaction: float = 0.2
    segment_length: int = 50
    init_weight: float = 1.0
    weights: list[float] = field(init=False)
    scores: list[float] = field(init=False)
    counts: list[int] = field(init=False)
    iterations: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.operators:
            raise ValueError("Need at least one operator.")
        self.weights = [self.init_weight for _ in self.operators]
        self.scores = [0.0 for _ in self.operators]
        self.counts = [0 for _ in self.operators]

    def select(self, rng: random.Random) -> tuple[int, T]:
        total = sum(self.weights)
        pick = rng.random() * total
        acc = 0.0
        for idx, weight in enumerate(self.weights):
            acc += weight
            if pick <= acc:
                return idx, self.operators[idx]
        return len(self.operators) - 1, self.operators[-1]

    def reward(self, idx: int, score: float) -> None:
        self.scores[idx] += score
        self.counts[idx] += 1

    def step(self) -> None:
        self.iterations += 1
        if self.iterations % self.segment_length != 0:
            return
        for i in range(len(self.weights)):
            if self.counts[i] > 0:
                avg = self.scores[i] / self.counts[i]
                self.weights[i] = (1 - self.reaction) * self.weights[i] + self.reaction * avg
        self.scores = [0.0 for _ in self.operators]
        self.counts = [0 for _ in self.operators]

    def summary(self) -> list[tuple[str, float]]:
        result = []
        for op, w in zip(self.operators, self.weights):
            result.append((getattr(op, "name", op.__class__.__name__), w))
        return result

