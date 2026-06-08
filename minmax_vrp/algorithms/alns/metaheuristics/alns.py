from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

from minmax_vrp.algorithms.alns.core.solution import Solution
from minmax_vrp.algorithms.alns.metaheuristics.acceptance import SimulatedAnnealing
from minmax_vrp.algorithms.alns.metaheuristics.selection import AdaptiveRouletteWheel, Operator
from minmax_vrp.algorithms.alns.metaheuristics.stopping import StopCriteria


@dataclass
class ALNSResult:
    best: Solution
    current: Solution
    iterations: int
    history: list[dict]
    destroy_weights: list[tuple[str, float]]
    repair_weights: list[tuple[str, float]]


@dataclass
class ALNS:
    destroy_operators: list[Operator]
    repair_operators: list[Operator]
    rng: random.Random = field(default_factory=random.Random)
    reaction: float = 0.2
    segment_length: int = 50
    scores: tuple[float, float, float, float] = (25.0, 10.0, 3.0, 0.5)
    local_search: Callable[[Solution, random.Random], Solution] | None = None

    def iterate(
        self,
        initial: Solution,
        stop: StopCriteria,
        acceptance: SimulatedAnnealing | None = None,
        collect_history: bool = True,
    ) -> ALNSResult:
        current = initial.copy()
        best = initial.copy()
        acceptance = acceptance or SimulatedAnnealing.auto_fit(initial, iterations=stop.max_iterations)

        destroy_selector = AdaptiveRouletteWheel(self.destroy_operators, self.reaction, self.segment_length)
        repair_selector = AdaptiveRouletteWheel(self.repair_operators, self.reaction, self.segment_length)
        history: list[dict] = []

        iteration = 0
        while not stop.should_stop(iteration):
            d_idx, destroy = destroy_selector.select(self.rng)
            r_idx, repair = repair_selector.select(self.rng)

            candidate = destroy(current, self.rng)
            candidate = repair(candidate, self.rng)
            if self.local_search is not None:
                candidate = self.local_search(candidate, self.rng)

            new_global_best = candidate.objective() < best.objective()
            better_than_current = candidate.objective() < current.objective()
            accepted = acceptance.accept(current, candidate, self.rng)

            if new_global_best:
                best = candidate.copy()
                current = candidate
                stop.mark_improvement(iteration)
                reward = self.scores[0]
                outcome = "best"
            elif accepted and better_than_current:
                current = candidate
                reward = self.scores[1]
                outcome = "better"
            elif accepted:
                current = candidate
                reward = self.scores[2]
                outcome = "accepted"
            else:
                reward = self.scores[3]
                outcome = "rejected"

            destroy_selector.reward(d_idx, reward)
            repair_selector.reward(r_idx, reward)
            destroy_selector.step()
            repair_selector.step()
            acceptance.step()

            if collect_history:
                history.append({
                    "iteration": iteration,
                    "best_max": best.max_route_length(),
                    "best_total": best.total_distance(),
                    "current_max": current.max_route_length(),
                    "current_total": current.total_distance(),
                    "destroy": getattr(destroy, "name", destroy.__class__.__name__),
                    "repair": getattr(repair, "name", repair.__class__.__name__),
                    "outcome": outcome,
                    "temperature": getattr(acceptance, "temperature", None),
                })
            iteration += 1

        return ALNSResult(
            best=best,
            current=current,
            iterations=iteration,
            history=history,
            destroy_weights=destroy_selector.summary(),
            repair_weights=repair_selector.summary(),
        )

