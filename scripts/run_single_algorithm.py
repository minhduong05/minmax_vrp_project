"""Run one algorithm on one input file and write a detailed single-run report."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from minmax_vrp.algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver  # noqa: E402
from minmax_vrp.io import read_instance, write_solution  # noqa: E402


REFERENCE_TRUE_VALUES = {"1", "true", "yes", "y"}


@dataclass(frozen=True)
class Reference:
    dataset: str
    instance: str
    k: int
    reference_type: str
    max_route: int
    total_distance: int
    balance: int
    return_to_depot: bool
    source: str
    source_file: str


def parse_bool(value: str) -> bool:
    return value.strip().lower() in REFERENCE_TRUE_VALUES


def infer_base_name(stem: str) -> str:
    match = re.match(r"(.+?)[_-]k\d+$", stem)
    if match:
        return match.group(1)
    return stem


def load_reference(data_root: Path, dataset: str, stem: str, k: int) -> Reference | None:
    reference_path = data_root / dataset / "reference.csv"
    if not reference_path.exists():
        return None

    wanted_names = {stem, infer_base_name(stem)}
    with reference_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            instance = row["instance"].strip()
            if instance not in wanted_names or int(row["k"]) != k:
                continue
            return Reference(
                dataset=dataset,
                instance=instance,
                k=k,
                reference_type=row.get("reference_type", "").strip(),
                max_route=int(row["objective_max_route"]),
                total_distance=int(row["total_distance"]),
                balance=int(row["amplitude"]),
                return_to_depot=parse_bool(row.get("return_to_depot", "")),
                source=row.get("source", "").strip(),
                source_file=row.get("source_file", "").strip(),
            )
    return None


def gap_percent(value: int, reference_value: int) -> str:
    if reference_value == 0:
        return ""
    return f"{((value - reference_value) / reference_value) * 100:.2f}"


def comparison_status(max_route: int, total_distance: int, reference: Reference | None) -> str:
    if reference is None:
        return "no_reference"
    if max_route < reference.max_route:
        return "better_max"
    if max_route > reference.max_route:
        return "worse_max"
    if total_distance < reference.total_distance:
        return "same_max_better_total"
    if total_distance > reference.total_distance:
        return "same_max_worse_total"
    return "matched"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Exactly one prepared .txt input file")
    parser.add_argument(
        "--algorithm",
        choices=ALGORITHM_NAMES,
        default="alns",
        help="Algorithm to run",
    )
    parser.add_argument("--data-root", default="data", help="Root folder containing benchmark data")
    parser.add_argument("--output-dir", default="outputs/single_run")
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--local-search", action="store_true")
    parser.add_argument("--local-search-rounds", type=int, default=2)

    return_group = parser.add_mutually_exclusive_group()
    return_group.add_argument(
        "--return-to-depot",
        dest="return_to_depot",
        action="store_true",
        default=None,
        help="Force return-to-depot evaluation",
    )
    return_group.add_argument(
        "--no-return-to-depot",
        dest="return_to_depot",
        action="store_false",
        help="Force open-route evaluation",
    )
    return parser


def validate_input(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"single run expects one .txt file, not a directory: {path}")
    if path.suffix.lower() != ".txt":
        raise ValueError(f"single run expects a .txt file: {path}")


def write_summary_text(path: Path, row: dict[str, object]) -> None:
    lines = [
        "Single Run Summary",
        "==================",
        f"dataset: {row['dataset']}",
        f"instance: {row['instance']}",
        f"input: {row['path']}",
        f"algorithm: {row['algorithm']}",
        f"n: {row['n']}",
        f"k: {row['k']}",
        f"feasible: {row['feasible']}",
        f"max_route: {row['max_route']}",
        f"min_route: {row['min_route']}",
        f"total_distance: {row['total_distance']}",
        f"balance: {row['balance']}",
        f"route_lengths: {row['route_lengths']}",
        f"runtime: {row['runtime']}",
        f"iterations: {row['iterations']}",
        f"return_to_depot: {row['return_to_depot']}",
        f"local_search: {row['local_search']}",
        f"seed: {row['seed']}",
        f"status: {row['status']}",
        f"reference_max_route: {row['reference_max_route']}",
        f"reference_total_distance: {row['reference_total_distance']}",
        f"max_route_gap: {row['max_route_gap']}",
        f"max_route_gap_percent: {row['max_route_gap_percent']}",
        f"solution_path: {row['solution_path']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(row: dict[str, object]) -> None:
    print("Single run finished")
    print(f"- input: {row['path']}")
    print(f"- algorithm: {row['algorithm']}")
    print(f"- feasible: {row['feasible']}")
    print(
        f"- objective: max={row['max_route']}, total={row['total_distance']}, "
        f"balance={row['balance']}, min={row['min_route']}"
    )
    print(f"- route_lengths: {row['route_lengths']}")
    print(f"- runtime: {row['runtime']}s, iterations={row['iterations']}")
    print(f"- status: {row['status']}")
    if row["has_reference"] == "yes":
        print(
            f"- reference: max={row['reference_max_route']}, "
            f"gap={row['max_route_gap']} ({row['max_route_gap_percent']}%)"
        )
    print(f"- solution: {row['solution_path']}")
    print(f"- summary_csv: {row['summary_csv_path']}")
    print(f"- summary_txt: {row['summary_txt_path']}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    validate_input(input_path)

    instance = read_instance(input_path)
    data_root = Path(args.data_root)
    dataset = input_path.parent.name
    reference = load_reference(data_root, dataset, input_path.stem, instance.k)
    include_return = args.return_to_depot
    if include_return is None:
        include_return = bool(reference and reference.return_to_depot)

    config = AlgorithmConfig(
        time_limit=args.time_limit,
        seed=args.seed,
        include_return_to_depot=include_return,
        use_local_search=args.local_search,
        local_search_rounds=args.local_search_rounds,
    )
    result = create_solver(args.algorithm, config).solve(instance)
    feasible = result.best.is_feasible(instance)
    route_lengths = result.best.route_lengths(instance)
    max_route, total_distance, balance = result.best_objective
    min_route = min(route_lengths) if route_lengths else 0

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = f"{input_path.stem}_{args.algorithm}"
    solution_path = output_dir / f"{output_prefix}_solution.txt"
    summary_csv_path = output_dir / f"{output_prefix}_summary.csv"
    summary_txt_path = output_dir / f"{output_prefix}_summary.txt"
    write_solution(result.best, solution_path)

    max_route_gap = max_route - reference.max_route if reference else ""
    max_route_gap_percent = gap_percent(max_route, reference.max_route) if reference else ""
    total_distance_gap = total_distance - reference.total_distance if reference else ""
    row: dict[str, object] = {
        "dataset": dataset,
        "instance": input_path.stem,
        "path": str(input_path),
        "n": instance.n,
        "k": instance.k,
        "algorithm": args.algorithm,
        "feasible": "yes" if feasible else "no",
        "max_route": max_route,
        "min_route": min_route,
        "total_distance": total_distance,
        "balance": balance,
        "route_lengths": " ".join(str(value) for value in route_lengths),
        "runtime": f"{result.runtime:.6f}",
        "iterations": result.iterations,
        "return_to_depot": "yes" if include_return else "no",
        "local_search": "yes" if args.local_search else "no",
        "seed": args.seed,
        "has_reference": "yes" if reference else "no",
        "reference_type": reference.reference_type if reference else "",
        "reference_max_route": reference.max_route if reference else "",
        "reference_total_distance": reference.total_distance if reference else "",
        "reference_balance": reference.balance if reference else "",
        "max_route_gap": max_route_gap,
        "max_route_gap_percent": max_route_gap_percent,
        "total_distance_gap": total_distance_gap,
        "status": comparison_status(max_route, total_distance, reference),
        "reference_source": reference.source if reference else "",
        "reference_source_file": reference.source_file if reference else "",
        "solution_path": str(solution_path),
        "summary_csv_path": str(summary_csv_path),
        "summary_txt_path": str(summary_txt_path),
    }
    fieldnames = list(row)
    with summary_csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)
    write_summary_text(summary_txt_path, row)
    print_summary(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
