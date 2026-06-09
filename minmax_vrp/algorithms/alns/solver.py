from __future__ import annotations

import random
import time
from dataclasses import dataclass, replace

from ...models import Instance, Objective, Solution
from ..route_constraints import has_positive_route_lengths
from .constructive.initial_solution import balanced_nearest_seed
from .core.instance import Instance as ALNSInstance
from .core.solution import Solution as ALNSSolution
from .metaheuristics.acceptance import SimulatedAnnealing
from .metaheuristics.alns import ALNS
from .metaheuristics.stopping import StopCriteria
from .operators.insertion import BalancedInsertion, GreedyMinMaxInsertion, RegretInsertion
from .operators.local_search import improve_by_relocate
from .operators.removal import (
    DestroyConfig,
    LongestRouteRemoval,
    RandomRemoval,
    RelatedRemoval,
    RouteRemoval,
    WorstRemoval,
)


@dataclass
class ALNSConfig:
    time_limit: float = 10.0
    seed: int = 99
    q_min_ratio: float | None = None
    q_max_ratio: float | None = None
    initial_temperature: float = 300.0
    cooling_rate: float | None = None
    reaction: float | None = None
    segment_length: int | None = None
    require_positive_route_lengths: bool = True
    use_local_search: bool = False
    max_iterations: int = 1_000_000

    reward_global_best: float = 10.0
    reward_current_improved: float = 5.0
    reward_accepted: float = 2.0
    reward_rejected: float = 0.0

    def __post_init__(self) -> None:
        if self.time_limit < 0.0:
            raise ValueError("time_limit must be non-negative")
        if self.q_min_ratio is not None and self.q_min_ratio < 0.0:
            raise ValueError("q_min_ratio must be non-negative")
        if (
            self.q_min_ratio is not None
            and self.q_max_ratio is not None
            and self.q_max_ratio < self.q_min_ratio
        ):
            raise ValueError("q_max_ratio must be greater than or equal to q_min_ratio")
        if self.initial_temperature < 0.0:
            raise ValueError("initial_temperature must be non-negative")
        if self.cooling_rate is not None and not 0.0 < self.cooling_rate <= 1.0:
            raise ValueError("cooling_rate must be in (0, 1]")
        if self.reaction is not None and not 0.0 <= self.reaction <= 1.0:
            raise ValueError("reaction must be in [0, 1]")
        if self.segment_length is not None and self.segment_length <= 0:
            raise ValueError("segment_length must be positive")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        rewards = [
            self.reward_global_best,
            self.reward_current_improved,
            self.reward_accepted,
            self.reward_rejected,
        ]
        if any(reward < 0.0 for reward in rewards):
            raise ValueError("ALNS rewards must be non-negative")

    def with_size_defaults(self, n: int) -> ALNSConfig:
        defaults = recommended_alns_defaults(n)
        return replace(
            self,
            q_min_ratio=self.q_min_ratio
            if self.q_min_ratio is not None
            else defaults["q_min_ratio"],
            q_max_ratio=self.q_max_ratio
            if self.q_max_ratio is not None
            else defaults["q_max_ratio"],
            cooling_rate=self.cooling_rate
            if self.cooling_rate is not None
            else defaults["cooling_rate"],
            reaction=self.reaction if self.reaction is not None else defaults["reaction"],
            segment_length=self.segment_length
            if self.segment_length is not None
            else defaults["segment_length"],
        )


def recommended_alns_defaults(n: int) -> dict[str, float | int]:
    if n <= 100:
        return {
            "q_min_ratio": 0.03,
            "q_max_ratio": 0.10,
            "cooling_rate": 0.999,
            "reaction": 0.10,
            "segment_length": 50,
        }
    if n <= 300:
        return {
            "q_min_ratio": 0.01,
            "q_max_ratio": 0.05,
            "cooling_rate": 0.999,
            "reaction": 0.10,
            "segment_length": 50,
        }
    if n <= 700:
        return {
            "q_min_ratio": 0.005,
            "q_max_ratio": 0.03,
            "cooling_rate": 0.9995,
            "reaction": 0.10,
            "segment_length": 100,
        }
    return {
        "q_min_ratio": 0.003,
        "q_max_ratio": 0.02,
        "cooling_rate": 0.999,
        "reaction": 0.10,
        "segment_length": 100,
    }


@dataclass
class ALNSResult:
    best: Solution
    iterations: int
    runtime: float
    best_objective: Objective
    destroy_weights: dict[str, float]
    repair_weights: dict[str, float]
    config: dict[str, float | int]


class ALNSSolver:
    """Adapter around the merged standalone ALNS implementation."""

    def __init__(self, config: ALNSConfig | None = None) -> None:
        self.config = config or ALNSConfig()

    def solve(self, instance: Instance, initial: Solution | None = None) -> ALNSResult:
        start = time.perf_counter()
        config = self.config.with_size_defaults(instance.n)
        if config.require_positive_route_lengths and instance.n < instance.k:
            raise ValueError(
                "ALNS requires every vehicle to have a positive-length route; "
                f"got n={instance.n}, k={instance.k}"
            )

        core_instance = _to_alns_instance(instance)
        rng = random.Random(config.seed)
        current = _to_alns_solution(core_instance, initial) if initial else balanced_nearest_seed(core_instance, rng)
        current.validate(strict_use_all_routes=config.require_positive_route_lengths)

        alns = self._build_alns(core_instance, config)
        stop = StopCriteria(
            max_iterations=config.max_iterations,
            max_seconds=config.time_limit,
        )
        acceptance = SimulatedAnnealing(
            start_temperature=config.initial_temperature,
            cooling_rate=float(config.cooling_rate),
        )
        result = alns.iterate(current, stop, acceptance, collect_history=False)
        best = _to_project_solution(result.best)

        if config.require_positive_route_lengths and not has_positive_route_lengths(best, instance):
            best = _to_project_solution(_ensure_all_routes_used(result.best))
        if config.require_positive_route_lengths and not has_positive_route_lengths(best, instance):
            raise ValueError(
                "ALNS requires every vehicle to have a positive-length route; "
                f"got n={instance.n}, k={instance.k}"
            )
        best.assert_feasible(instance)

        runtime = time.perf_counter() - start
        return ALNSResult(
            best=best,
            iterations=result.iterations,
            runtime=runtime,
            best_objective=best.evaluate(instance).as_tuple(),
            destroy_weights=dict(result.destroy_weights),
            repair_weights=dict(result.repair_weights),
            config=_config_dict(config),
        )

    def _build_alns(self, instance: ALNSInstance, config: ALNSConfig) -> ALNS:
        min_remove = max(1, min(instance.n, int(float(config.q_min_ratio) * instance.n)))
        destroy_config = DestroyConfig(
            min_remove=min_remove,
            max_remove_fraction=float(config.q_max_ratio),
        )
        destroys = [
            RandomRemoval(destroy_config),
            WorstRemoval(destroy_config, focus_longest=True),
            LongestRouteRemoval(destroy_config),
            RelatedRemoval(destroy_config),
            RouteRemoval(destroy_config, partial=True),
        ]
        repairs = [
            GreedyMinMaxInsertion(),
            RegretInsertion(k=2),
            BalancedInsertion(),
        ]

        def local(solution: ALNSSolution, rng: random.Random) -> ALNSSolution:
            candidate = solution
            if config.use_local_search:
                candidate = improve_by_relocate(candidate, max_checks=1500, rng=rng)
            if config.require_positive_route_lengths:
                candidate = _ensure_all_routes_used(candidate)
            return candidate

        return ALNS(
            destroys,
            repairs,
            rng=random.Random(config.seed),
            reaction=float(config.reaction),
            segment_length=int(config.segment_length),
            scores=(
                config.reward_global_best,
                config.reward_current_improved,
                config.reward_accepted,
                config.reward_rejected,
            ),
            local_search=local,
        )


def _config_dict(config: ALNSConfig) -> dict[str, float | int]:
    return {
        "q_min_ratio": float(config.q_min_ratio),
        "q_max_ratio": float(config.q_max_ratio),
        "initial_temperature": config.initial_temperature,
        "cooling_rate": float(config.cooling_rate),
        "reaction": float(config.reaction),
        "segment_length": int(config.segment_length),
        "reward_global_best": config.reward_global_best,
        "reward_current_improved": config.reward_current_improved,
        "reward_accepted": config.reward_accepted,
        "reward_rejected": config.reward_rejected,
    }


def _to_alns_instance(instance: Instance) -> ALNSInstance:
    return ALNSInstance(
        n=instance.n,
        k=instance.k,
        distance=tuple(tuple(float(value) for value in row) for row in instance.distance),
        return_to_depot=False,
    )


def _to_alns_solution(instance: ALNSInstance, solution: Solution) -> ALNSSolution:
    return ALNSSolution(instance, [route[:] for route in solution.routes])


def _to_project_solution(solution: ALNSSolution) -> Solution:
    return Solution([route[:] for route in solution.routes])


def _ensure_all_routes_used(solution: ALNSSolution) -> ALNSSolution:
    repaired = solution.copy()
    empty_routes = [idx for idx, route in enumerate(repaired.routes) if len(route) <= 1]
    for empty_idx in empty_routes:
        donors = [idx for idx, route in enumerate(repaired.routes) if len(route) > 2]
        if not donors:
            break
        best_move: tuple[tuple[tuple[float, ...], float], int, int] | None = None
        for donor_idx in donors:
            for pos in range(1, len(repaired.routes[donor_idx])):
                customer = repaired.routes[donor_idx][pos]
                trial = repaired.copy()
                trial.remove_at(donor_idx, pos, add_to_unassigned=False)
                trial.insert_customer(empty_idx, 1, customer)
                item = (trial.objective(), donor_idx, pos)
                if best_move is None or item < best_move:
                    best_move = item
        if best_move is None:
            break
        _, donor_idx, pos = best_move
        customer = repaired.remove_at(donor_idx, pos, add_to_unassigned=False)
        repaired.insert_customer(empty_idx, 1, customer)
    return repaired
