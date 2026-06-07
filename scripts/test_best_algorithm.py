"""Evaluate one tuned algorithm on the held-out test split.

This script is for final evaluation, not tuning. Run it once per algorithm, then
combine the generated *_runs.csv files with compare_best_algorithm_results.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser import load_instance
from minmax_vrp.algorithms.alns.solver import ALNSConfig, ALNSSolver
from minmax_vrp.algorithms.tabu_search.tabu_search import local_clear, tabu_search
from minmax_vrp.algorithms.vns import submit_vns
from minmax_vrp.models import Instance, Solution


ALGORITHM_CHOICES = ("alns", "vns", "tabu_search")
DEFAULT_INSTANCE_FILE = "data/splits/test_seed02_seed03.txt"
DEFAULT_OUTPUT_DIR = "output/algorithm_comparison"

BEST_ALNS_CONFIG = {
    "q_min_ratio": 0.02,
    "q_max_ratio": 0.10,
    "initial_temperature": 300.0,
    "cooling_rate": 0.999,
    "reward_global_best": 20.0,
    "reward_current_improved": 5.0,
    "reward_accepted": 1.0,
    "reward_rejected": 0.0,
}

BEST_VNS_CONFIG = {
    "max_shake_level": 10,
    "candidate_limit": 24,
}

BEST_TABU_CONFIG = {
    "tenure": 15,
    "max_candidates": 200,
    "use_local_search": True,
}

CSV_HEADER = [
    "timestamp",
    "algorithm",
    "config_name",
    "config_json",
    "instance",
    "family",
    "n",
    "k",
    "data_seed",
    "solver_seed",
    "time_limit",
    "feasible",
    "max_route",
    "total_distance",
    "balance",
    "runtime",
    "iterations",
]

SUMMARY_HEADER = [
    "timestamp",
    "algorithm",
    "config_name",
    "group_type",
    "group_key",
    "runs",
    "feasible_rate",
    "mean_max_route",
    "std_max_route",
    "median_max_route",
    "mean_total_distance",
    "mean_balance",
    "mean_runtime",
    "mean_iterations",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=ALGORITHM_CHOICES, required=True)
    parser.add_argument(
        "--instances",
        nargs="+",
        help="Explicit instance paths. Overrides --instance-file.",
    )
    parser.add_argument("--instance-file", default=DEFAULT_INSTANCE_FILE)
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--stamp",
        help="Optional fixed output stamp. By default a timestamp is generated.",
    )
    return parser


def read_instance_file(path: str) -> list[str]:
    out = []
    for raw_line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def family_from_path(path: str) -> str:
    parts = Path(path).parts
    if "generated" in parts:
        idx = parts.index("generated")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def data_seed_from_path(path: str) -> str:
    stem = Path(path).stem
    for token in stem.split("_"):
        if token.startswith("seed"):
            return token.replace("seed", "")
    return ""


def config_name(algorithm: str) -> str:
    if algorithm == "alns":
        return "small_destroy__strict__aggressive_best"
    if algorithm == "vns":
        return "shake10__cand24"
    if algorithm == "tabu_search":
        return "tenure15_cand200"
    raise ValueError(algorithm)


def config_json(algorithm: str) -> str:
    if algorithm == "alns":
        config = BEST_ALNS_CONFIG
    elif algorithm == "vns":
        config = BEST_VNS_CONFIG
    elif algorithm == "tabu_search":
        config = BEST_TABU_CONFIG
    else:
        raise ValueError(algorithm)
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def solve_alns(instance: Instance, time_limit: float, seed: int):
    config = ALNSConfig(time_limit=time_limit, seed=seed, **BEST_ALNS_CONFIG)
    result = ALNSSolver(config).solve(instance)
    return result.best, result.runtime, result.iterations


def solve_vns(instance: Instance, time_limit: float, seed: int):
    old_time_limit = submit_vns.TIME_LIMIT
    old_seed = submit_vns.RANDOM_SEED
    old_shake = submit_vns.MAX_SHAKE_LEVEL
    old_candidate = submit_vns.CANDIDATE_LIMIT
    try:
        submit_vns.TIME_LIMIT = max(0.0, time_limit)
        submit_vns.RANDOM_SEED = seed
        submit_vns.MAX_SHAKE_LEVEL = BEST_VNS_CONFIG["max_shake_level"]
        submit_vns.CANDIDATE_LIMIT = BEST_VNS_CONFIG["candidate_limit"]
        start = time.perf_counter()
        routes, stats = submit_vns.solve(instance, return_stats=True)
        runtime = time.perf_counter() - start
        return Solution(routes), runtime, int(stats["iterations"])
    finally:
        submit_vns.TIME_LIMIT = old_time_limit
        submit_vns.RANDOM_SEED = old_seed
        submit_vns.MAX_SHAKE_LEVEL = old_shake
        submit_vns.CANDIDATE_LIMIT = old_candidate


def solve_tabu_search(instance: Instance, time_limit: float, seed: int):
    del seed  # Current Tabu implementation is deterministic.
    max_iterations = max(1, int(max(0.01, time_limit) * 200))
    start = time.perf_counter()
    routes, _, iterations_done = tabu_search(
        instance.n,
        instance.k,
        instance.distance,
        max_inter=max_iterations,
        tenure=BEST_TABU_CONFIG["tenure"],
        max_candidates=BEST_TABU_CONFIG["max_candidates"],
        deadline=start + max(0.0, time_limit),
    )
    if BEST_TABU_CONFIG["use_local_search"]:
        routes = local_clear(routes, instance.distance)
    runtime = time.perf_counter() - start
    return Solution(routes), runtime, iterations_done


def solve_once(algorithm: str, instance: Instance, time_limit: float, seed: int):
    if algorithm == "alns":
        return solve_alns(instance, time_limit, seed)
    if algorithm == "vns":
        return solve_vns(instance, time_limit, seed)
    if algorithm == "tabu_search":
        return solve_tabu_search(instance, time_limit, seed)
    raise ValueError(algorithm)


def row_group_key(row: dict[str, object], group_type: str) -> str:
    if group_type == "overall":
        return "all"
    if group_type == "size":
        return f"n={row['n']},k={row['k']}"
    if group_type == "family":
        return str(row["family"])
    raise ValueError(group_type)


def summarize(rows: list[dict[str, object]], timestamp: str) -> list[dict[str, object]]:
    summary_rows = []
    for group_type in ("overall", "size", "family"):
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[row_group_key(row, group_type)].append(row)
        for group_key, group in sorted(grouped.items()):
            max_routes = [float(row["max_route"]) for row in group]
            total_distances = [float(row["total_distance"]) for row in group]
            balances = [float(row["balance"]) for row in group]
            runtimes = [float(row["runtime"]) for row in group]
            iterations = [int(row["iterations"]) for row in group]
            feasible = [str(row["feasible"]) == "yes" for row in group]
            summary_rows.append(
                {
                    "timestamp": timestamp,
                    "algorithm": group[0]["algorithm"],
                    "config_name": group[0]["config_name"],
                    "group_type": group_type,
                    "group_key": group_key,
                    "runs": len(group),
                    "feasible_rate": sum(feasible) / len(feasible),
                    "mean_max_route": statistics.mean(max_routes),
                    "std_max_route": statistics.pstdev(max_routes)
                    if len(max_routes) > 1
                    else 0.0,
                    "median_max_route": statistics.median(max_routes),
                    "mean_total_distance": statistics.mean(total_distances),
                    "mean_balance": statistics.mean(balances),
                    "mean_runtime": statistics.mean(runtimes),
                    "mean_iterations": statistics.mean(iterations),
                }
            )
    return summary_rows


def write_csv(path: Path, rows: list[dict[str, object]], header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = build_parser().parse_args()
    seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
    instance_paths = args.instances or read_instance_file(args.instance_file)
    timestamp = datetime.now().isoformat(timespec="seconds")
    stamp = args.stamp or datetime.now().strftime("%Y%m%d_%H%M%S")

    rows = []
    total_runs = len(instance_paths) * len(seeds)
    run_index = 0
    for raw_path in instance_paths:
        instance = load_instance(ROOT / raw_path)
        for seed in seeds:
            run_index += 1
            print(
                f"[{run_index}/{total_runs}] {args.algorithm} "
                f"{Path(raw_path).name} seed={seed}",
                flush=True,
            )
            solution, runtime, iterations = solve_once(
                args.algorithm,
                instance,
                args.time_limit,
                seed,
            )
            feasible = solution.is_feasible(instance)
            objective = solution.evaluate(instance)
            rows.append(
                {
                    "timestamp": timestamp,
                    "algorithm": args.algorithm,
                    "config_name": config_name(args.algorithm),
                    "config_json": config_json(args.algorithm),
                    "instance": raw_path,
                    "family": family_from_path(raw_path),
                    "n": instance.n,
                    "k": instance.k,
                    "data_seed": data_seed_from_path(raw_path),
                    "solver_seed": seed,
                    "time_limit": args.time_limit,
                    "feasible": "yes" if feasible else "no",
                    "max_route": objective.max_route_length,
                    "total_distance": objective.total_distance,
                    "balance": objective.balance,
                    "runtime": runtime,
                    "iterations": iterations,
                }
            )

    output_dir = ROOT / args.output_dir
    prefix = f"{stamp}_{args.algorithm}_best_test"
    runs_path = output_dir / f"{prefix}_runs.csv"
    summary_path = output_dir / f"{prefix}_summary.csv"
    write_csv(runs_path, rows, CSV_HEADER)
    write_csv(summary_path, summarize(rows, timestamp), SUMMARY_HEADER)
    print(f"Wrote runs: {runs_path}")
    print(f"Wrote summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
