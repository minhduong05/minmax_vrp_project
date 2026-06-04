"""CLI runner that parses raw data in memory and solves one instance."""

from __future__ import annotations

import argparse
from pathlib import Path

from parser import load_instance
from minmax_vrp.algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver
from minmax_vrp.io import format_distance, format_solution, write_solution


def default_algorithm() -> str:
    if "alns" in ALGORITHM_NAMES:
        return "alns"
    if not ALGORITHM_NAMES:
        raise RuntimeError("no algorithms are registered")
    return ALGORITHM_NAMES[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", help="Raw .tsp/.vrp file, or generated .txt matrix file")
    parser.add_argument(
        "-k",
        "--k",
        type=int,
        help="Number of routes. Required when it cannot be inferred from the file name.",
    )
    parser.add_argument(
        "--algorithm",
        choices=ALGORITHM_NAMES,
        default=default_algorithm(),
        help="Solver algorithm",
    )
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--local-search", action="store_true")
    parser.add_argument("--local-search-rounds", type=int, default=2)
    parser.add_argument("--q-min-ratio", type=float, default=0.05)
    parser.add_argument("--q-max-ratio", type=float, default=0.20)
    parser.add_argument("--q-min-cap", type=int, default=6)
    parser.add_argument("--q-max-cap", type=int, default=24)
    parser.add_argument(
        "--no-return-to-depot",
        action="store_true",
        help="Use open routes. Default is closed routes: 0 -> ... -> 0.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to write the solution route file.",
    )
    parser.add_argument("--print-solution", action="store_true", help="Print solution routes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instance_path = Path(args.instance)
    instance = load_instance(instance_path, k=args.k)
    include_return_to_depot = not args.no_return_to_depot

    config = AlgorithmConfig(
        time_limit=args.time_limit,
        seed=args.seed,
        include_return_to_depot=include_return_to_depot,
        use_local_search=args.local_search,
        local_search_rounds=args.local_search_rounds,
        q_min_ratio=args.q_min_ratio,
        q_max_ratio=args.q_max_ratio,
        q_min_cap=args.q_min_cap,
        q_max_cap=args.q_max_cap,
    )
    result = create_solver(args.algorithm, config).solve(instance)
    feasible = result.best.is_feasible(instance)
    lengths = result.best.route_lengths(instance)
    objective = result.best.evaluate(instance)

    if args.output:
        write_solution(result.best, args.output)
    if args.print_solution:
        print(format_solution(result.best))

    print("Run Summary")
    print(f"input: {instance_path}")
    print(f"algorithm: {result.algorithm}")
    print(f"n: {instance.n}")
    print(f"k: {instance.k}")
    print(f"return_to_depot: {'yes' if include_return_to_depot else 'no'}")
    print(f"feasible: {'yes' if feasible else 'no'}")
    print(f"max_route: {format_distance(objective.max_route_length)}")
    print(f"total_distance: {format_distance(objective.total_distance)}")
    print(f"balance: {format_distance(objective.balance)}")
    print(f"route_lengths: {' '.join(format_distance(value) for value in lengths)}")
    print(f"runtime: {result.runtime:.6f}s")
    print(f"iterations: {result.iterations}")
    if args.output:
        print(f"solution: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
