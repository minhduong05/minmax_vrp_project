import argparse
import sys

from .algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver
from .io import format_solution, read_instance, write_solution


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solvers for min-max parcel pickup routing")
    parser.add_argument("input", help="Path to input file")
    parser.add_argument("-o", "--output", help="Path to output file. If omitted, prints to stdout")
    parser.add_argument(
        "--algorithm",
        choices=ALGORITHM_NAMES,
        default="alns",
        help="Algorithm to run",
    )
    parser.add_argument("--time-limit", type=float, default=10.0, help="Runtime limit in seconds")
    parser.add_argument("--seed", type=int, default=99, help="Random seed")
    parser.add_argument("--q-min-ratio", type=float, default=0.05, help="Minimum removal ratio")
    parser.add_argument("--q-max-ratio", type=float, default=0.20, help="Maximum removal ratio")
    parser.add_argument("--q-min-cap", type=int, default=6, help="Maximum lower bound for removed points")
    parser.add_argument("--q-max-cap", type=int, default=24, help="Maximum upper bound for removed points")
    parser.add_argument("--local-search", action="store_true", help="Enable post-repair local search")
    parser.add_argument("--no-local-search", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--return-to-depot",
        action="store_true",
        help="Evaluate each route with an additional edge from last node back to depot",
    )
    parser.add_argument("--verbose", action="store_true", help="Print solving statistics to stderr")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    instance = read_instance(args.input)
    config = AlgorithmConfig(
        time_limit=args.time_limit,
        seed=args.seed,
        q_min_ratio=args.q_min_ratio,
        q_max_ratio=args.q_max_ratio,
        q_min_cap=args.q_min_cap,
        q_max_cap=args.q_max_cap,
        use_local_search=args.local_search and not args.no_local_search,
        include_return_to_depot=args.return_to_depot,
    )
    solver = create_solver(args.algorithm, config)
    result = solver.solve(instance)

    if args.output:
        write_solution(result.best, args.output)
    else:
        print(format_solution(result.best))

    if args.verbose:
        print(
            f"algorithm={result.algorithm}, iterations={result.iterations}, runtime={result.runtime:.3f}s, "
            f"objective(max,total,balance)={result.best_objective}",
            file=sys.stderr,
        )
        for key, value in result.stats.items():
            print(f"{key}={value}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
