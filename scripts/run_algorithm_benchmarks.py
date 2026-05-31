"""Run benchmark algorithms and compare references when available."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

from minmax_vrp.algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver
from minmax_vrp.io import read_instance, write_solution


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


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", str(path))
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def parse_algorithms(raw_value: str) -> list[str]:
    if raw_value == "all":
        return list(ALGORITHM_NAMES)
    algorithms = [value.strip() for value in raw_value.split(",") if value.strip()]
    unknown = [value for value in algorithms if value not in ALGORITHM_NAMES]
    if unknown:
        choices = ", ".join(ALGORITHM_NAMES)
        raise argparse.ArgumentTypeError(f"unknown algorithms {unknown}; choices: {choices}, all")
    return algorithms


def parse_bool(value: str) -> bool:
    return value.strip().lower() in REFERENCE_TRUE_VALUES


def infer_base_name(stem: str) -> str:
    match = re.match(r"(.+?)[_-]k\d+$", stem)
    if match:
        return match.group(1)
    return stem


def is_raw_data_path(path: Path) -> bool:
    return "raw" in {part.lower() for part in path.parts}


def collect_default_inputs(data_root: Path) -> list[Path]:
    files: list[Path] = []
    for dataset_dir in data_root.iterdir():
        if (
            not dataset_dir.is_dir()
            or dataset_dir.name == "raw"
            or dataset_dir.name.startswith(".")
        ):
            continue
        files.extend(dataset_dir.glob("*.txt"))
    return sorted(files, key=natural_key)


def collect_inputs(paths: list[str], data_root: Path) -> list[Path]:
    if not paths:
        return collect_default_inputs(data_root)

    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            files.append(path)
        elif path.resolve() == data_root.resolve():
            files.extend(collect_default_inputs(data_root))
        elif path.is_dir():
            files.extend(child for child in path.glob("*.txt") if not is_raw_data_path(child))
        else:
            raise FileNotFoundError(f"input path not found: {path}")
    return sorted(files, key=natural_key)


def load_references(data_root: Path) -> dict[tuple[str, str, int], Reference]:
    references: dict[tuple[str, str, int], Reference] = {}
    for reference_path in sorted(data_root.glob("*/reference.csv"), key=natural_key):
        dataset = reference_path.parent.name
        with reference_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                instance = row["instance"].strip()
                k = int(row["k"])
                reference = Reference(
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
                references[(dataset, instance, k)] = reference
    return references


def find_reference(
    references: dict[tuple[str, str, int], Reference],
    dataset: str,
    stem: str,
    k: int,
) -> Reference | None:
    base_name = infer_base_name(stem)
    return references.get((dataset, base_name, k)) or references.get((dataset, stem, k))


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


def reference_value(reference: Reference | None) -> str:
    if reference is None:
        return "-"
    return str(reference.max_route)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Benchmark files or directories. Default: every prepared dataset under data/",
    )
    parser.add_argument("--data-root", default="data", help="Root folder containing benchmark data")
    parser.add_argument(
        "--algorithms",
        type=parse_algorithms,
        default=list(ALGORITHM_NAMES),
        help="Comma-separated algorithm names or 'all'",
    )
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--local-search", action="store_true")
    parser.add_argument("--local-search-rounds", type=int, default=2)
    parser.add_argument("--max-instances", type=int, help="Smoke-test only the first N inputs")
    parser.add_argument(
        "-o",
        "--output",
        default="outputs/logs/algorithm_comparison.csv",
        help="CSV summary output path",
    )
    parser.add_argument(
        "--solutions-dir",
        default="outputs/experiments/algorithm_benchmarks",
        help="Directory for per-instance solution files",
    )
    parser.add_argument("--no-solutions", action="store_true", help="Do not write solution files")

    return_group = parser.add_mutually_exclusive_group()
    return_group.add_argument(
        "--return-to-depot",
        dest="return_to_depot",
        action="store_true",
        default=None,
        help="Force return-to-depot evaluation for every instance",
    )
    return_group.add_argument(
        "--no-return-to-depot",
        dest="return_to_depot",
        action="store_false",
        help="Force open-route evaluation for every instance",
    )
    return parser


def build_config(args: argparse.Namespace, include_return_to_depot: bool) -> AlgorithmConfig:
    return AlgorithmConfig(
        time_limit=args.time_limit,
        seed=args.seed,
        include_return_to_depot=include_return_to_depot,
        use_local_search=args.local_search,
        local_search_rounds=args.local_search_rounds,
    )


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_log_files(
    rows: list[dict[str, object]],
    fieldnames: list[str],
    output_path: Path,
) -> list[Path]:
    log_dir = output_path.parent
    written_paths = [write_csv(output_path, fieldnames, rows)]

    for algorithm in ALGORITHM_NAMES:
        algorithm_rows = [row for row in rows if row["algorithm"] == algorithm]
        algorithm_path = log_dir / f"{algorithm}_results.csv"
        written_paths.append(write_csv(algorithm_path, fieldnames, algorithm_rows))

    reference_rows = [row for row in rows if row["has_reference"] == "yes"]
    no_reference_rows = [row for row in rows if row["has_reference"] == "no"]
    written_paths.append(
        write_csv(log_dir / "comparison_with_reference.csv", fieldnames, reference_rows)
    )
    written_paths.append(
        write_csv(log_dir / "comparison_without_reference.csv", fieldnames, no_reference_rows)
    )
    return written_paths


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_root = Path(args.data_root)
    references = load_references(data_root)
    files = collect_inputs(args.inputs, data_root)
    if args.max_instances is not None:
        files = files[: args.max_instances]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    solutions_dir = Path(args.solutions_dir)
    if not args.no_solutions:
        solutions_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    print(
        f"{'dataset':<18} {'instance':<20} {'algorithm':<18} {'n':>5} {'k':>4} "
        f"{'max':>8} {'ref':>8} {'gap%':>8} {'runtime':>8} status"
    )
    print("-" * 118)

    for file_path in files:
        dataset = file_path.parent.name
        instance = read_instance(file_path)
        reference = find_reference(references, dataset, file_path.stem, instance.k)
        include_return = args.return_to_depot
        if include_return is None:
            include_return = bool(reference and reference.return_to_depot)
        config = build_config(args, include_return)

        for algorithm in args.algorithms:
            result = create_solver(algorithm, config).solve(instance)
            result.best.assert_feasible(instance)
            max_route, total_distance, balance = result.best_objective
            status = comparison_status(max_route, total_distance, reference)
            max_route_gap = max_route - reference.max_route if reference else ""
            max_route_gap_percent = gap_percent(max_route, reference.max_route) if reference else ""
            total_distance_gap = total_distance - reference.total_distance if reference else ""

            solution_path = ""
            if not args.no_solutions:
                solution_file = solutions_dir / dataset / algorithm / f"{file_path.stem}.txt"
                solution_file.parent.mkdir(parents=True, exist_ok=True)
                write_solution(result.best, solution_file)
                solution_path = str(solution_file)

            rows.append(
                {
                    "dataset": dataset,
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
                    "return_to_depot": "yes" if include_return else "no",
                    "local_search": "yes" if args.local_search else "no",
                    "has_reference": "yes" if reference else "no",
                    "reference_type": reference.reference_type if reference else "",
                    "reference_max_route": reference.max_route if reference else "",
                    "reference_total_distance": reference.total_distance if reference else "",
                    "reference_balance": reference.balance if reference else "",
                    "max_route_gap": max_route_gap,
                    "max_route_gap_percent": max_route_gap_percent,
                    "total_distance_gap": total_distance_gap,
                    "status": status,
                    "reference_source": reference.source if reference else "",
                    "reference_source_file": reference.source_file if reference else "",
                    "solution_path": solution_path,
                }
            )

            gap_text = gap_percent(max_route, reference.max_route) if reference else "-"
            print(
                f"{dataset:<18} {file_path.stem:<20} {algorithm:<18} "
                f"{instance.n:>5} {instance.k:>4} {max_route:>8} "
                f"{reference_value(reference):>8} {gap_text:>8} "
                f"{result.runtime:>8.3f} {status}"
            )

    fieldnames = [
        "dataset",
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
        "has_reference",
        "reference_type",
        "reference_max_route",
        "reference_total_distance",
        "reference_balance",
        "max_route_gap",
        "max_route_gap_percent",
        "total_distance_gap",
        "status",
        "reference_source",
        "reference_source_file",
        "solution_path",
    ]
    written_paths = write_log_files(rows, fieldnames, output_path)

    print(f"\nWrote {len(rows)} rows across {len(written_paths)} CSV log files:")
    for path in written_paths:
        print(f"- {path}")
    if not args.no_solutions:
        print(f"Wrote solutions under {solutions_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
