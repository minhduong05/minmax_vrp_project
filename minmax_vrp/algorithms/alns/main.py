from __future__ import annotations

import argparse
import random
from pathlib import Path

from minmax_vrp.algorithms.alns.constructive.initial_solution import balanced_nearest_seed
from minmax_vrp.algorithms.alns.core.instance import Instance
from minmax_vrp.algorithms.alns.metaheuristics.alns import ALNS
from minmax_vrp.algorithms.alns.metaheuristics.acceptance import SimulatedAnnealing
from minmax_vrp.algorithms.alns.metaheuristics.stopping import StopCriteria
from minmax_vrp.algorithms.alns.operators.insertion import BalancedInsertion, GreedyMinMaxInsertion, RegretInsertion
from minmax_vrp.algorithms.alns.operators.local_search import improve_by_relocate
from minmax_vrp.algorithms.alns.operators.removal import (
    DestroyConfig,
    LongestRouteRemoval,
    RandomRemoval,
    RelatedRemoval,
    RouteRemoval,
    WorstRemoval,
)


def build_default_alns(seed: int, max_remove_fraction: float, use_local_search: bool) -> ALNS:
    rng = random.Random(seed)
    config = DestroyConfig(min_remove=1, max_remove_fraction=max_remove_fraction)
    destroys = [
        RandomRemoval(config),
        WorstRemoval(config, focus_longest=True),
        LongestRouteRemoval(config),
        RelatedRemoval(config),
        RouteRemoval(config, partial=True),
    ]
    repairs = [
        GreedyMinMaxInsertion(),
        RegretInsertion(k=2),
        BalancedInsertion(),
    ]
    local = (lambda sol, r: improve_by_relocate(sol, max_checks=1500, rng=r)) if use_local_search else None
    return ALNS(destroys, repairs, rng=rng, local_search=local)


def solve(args: argparse.Namespace) -> None:
    instance = Instance.from_file(args.input, return_to_depot=args.return_to_depot)
    rng = random.Random(args.seed)
    initial = balanced_nearest_seed(instance, rng)

    alns = build_default_alns(args.seed, args.remove_fraction, args.local_search)
    stop = StopCriteria(
        max_iterations=args.iterations,
        max_seconds=args.time_limit,
        no_improve_iterations=args.no_improve,
    )
    acceptance = SimulatedAnnealing.auto_fit(initial, iterations=args.iterations)
    result = alns.iterate(initial, stop, acceptance, collect_history=args.history is not None)

    result.best.validate(strict_use_all_routes=args.strict_use_all_routes)

    if args.output:
        Path(args.output).write_text(result.best.to_output_text(), encoding="utf-8")
    else:
        print(result.best.to_output_text(), end="")

    if args.history:
        lines = ["iteration,best_max,best_total,current_max,current_total,destroy,repair,outcome,temperature"]
        for row in result.history:
            lines.append(
                f"{row['iteration']},{row['best_max']},{row['best_total']},{row['current_max']},{row['current_total']},"
                f"{row['destroy']},{row['repair']},{row['outcome']},{row['temperature']}"
            )
        Path(args.history).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Best max route length: {result.best.max_route_length():.6f}")
    print(f"Best total distance: {result.best.total_distance():.6f}")
    print(f"Balance: {result.best.balance():.6f}")
    print(f"Iterations: {result.iterations}")
    print("Destroy weights:", result.destroy_weights)
    print("Repair weights:", result.repair_weights)


def main() -> None:
    parser = argparse.ArgumentParser(description="ALNS for Min-Max Vehicle Routing")
    parser.add_argument("input", help="Input file: distance matrix or coordinates")
    parser.add_argument("-o", "--output", help="Output solution file")
    parser.add_argument("--history", help="CSV file to store convergence history")
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--no-improve", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--remove-fraction", type=float, default=0.05)
    parser.add_argument("--return-to-depot", action="store_true")
    parser.add_argument("--local-search", action="store_true")
    parser.add_argument("--strict-use-all-routes", action="store_true", default=True)
    args = parser.parse_args()
    solve(args)


if __name__ == "__main__":
    main()

