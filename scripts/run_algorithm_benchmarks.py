"""Run one or more algorithms on benchmark files and write a CSV summary."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from minmax_vrp.algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver
from minmax_vrp.io import read_instance


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def collect_inputs(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(path.glob("*.txt"))
        else:
            files.append(path)
    return sorted(files, key=natural_key)


def parse_algorithms(raw_value: str) -> list[str]:
    if raw_value == "all":
        return list(ALGORITHM_NAMES)
    algorithms = [value.strip() for value in raw_value.split(",") if value.strip()]
    unknown = [value for value in algorithms if value not in ALGORITHM_NAMES]
    if unknown:
        choices = ", ".join(ALGORITHM_NAMES)
        raise argparse.ArgumentTypeError(f"unknown algorithms {unknown}; choices: {choices}, all")
    return algorithms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Benchmark files or directories")
    parser.add_argument(
        "--algorithms",
        type=parse_algorithms,
        default=list(ALGORITHM_NAMES),
        help="Comma-separated algorithm names or 'all'",
    )
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--local-search", action="store_true")
    parser.add_argument("--return-to-depot", action="store_true")
    parser.add_argument(
        "-o",
        "--output",
        default="outputs/logs/algorithm_comparison.csv",
        help="CSV output path",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = collect_inputs(args.inputs)

    config = AlgorithmConfig(
        time_limit=args.time_limit,
        seed=args.seed,
        use_local_search=args.local_search,
        include_return_to_depot=args.return_to_depot,
    )

    rows: list[dict[str, object]] = []
    for file_path in files:
        instance = read_instance(file_path)
        for algorithm in args.algorithms:
            solver = create_solver(algorithm, config)
            result = solver.solve(instance)
            max_route, total_distance, balance = result.best_objective
            rows.append(
                {
                    "instance": file_path.stem,
                    "path": str(file_path),
                    "n": instance.n,
                    "k": instance.k,
                    "algorithm": algorithm,
                    "max_route": max_route,
                    "total_distance": total_distance,
                    "balance": balance,
                    "runtime": f"{result.runtime:.6f}",
                    "iterations": result.iterations,
                    "return_to_depot": "yes" if args.return_to_depot else "no",
                    "local_search": "yes" if args.local_search else "no",
                }
            )

    fieldnames = [
        "instance",
        "path",
        "n",
        "k",
        "algorithm",
        "max_route",
        "total_distance",
        "balance",
        "runtime",
        "iterations",
        "return_to_depot",
        "local_search",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
