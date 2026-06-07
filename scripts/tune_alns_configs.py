"""Tune ALNS hyperparameter groups in staged experiments.

Stages:
1. Run the baseline.
2. Tune destroy size while SA and reward stay fixed.
3. Tune SA over the top destroy configs.
4. Tune reward over the best destroy and SA configs.
5. Validate top destroy x top SA x top reward combinations.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from parser import load_instance
from minmax_vrp.algorithms.alns.solver import ALNSConfig, ALNSSolver


DESTROY_CONFIGS = [
    {"name": "small_destroy", "q_min_ratio": 0.02, "q_max_ratio": 0.10},
    {"name": "medium_destroy", "q_min_ratio": 0.05, "q_max_ratio": 0.20},
    {"name": "large_destroy", "q_min_ratio": 0.10, "q_max_ratio": 0.30},
    {"name": "very_large_destroy", "q_min_ratio": 0.15, "q_max_ratio": 0.40},
]

SA_CONFIGS = [
    {"name": "strict", "initial_temperature": 300.0, "cooling_rate": 0.999},
    {"name": "balanced", "initial_temperature": 500.0, "cooling_rate": 0.9995},
    {"name": "default", "initial_temperature": 1000.0, "cooling_rate": 0.999},
    {"name": "default_slow", "initial_temperature": 1000.0, "cooling_rate": 0.9995},
    {"name": "very_exploratory", "initial_temperature": 1000.0, "cooling_rate": 0.9999},
]

REWARD_CONFIGS = [
    {
        "name": "default",
        "reward_global_best": 10.0,
        "reward_current_improved": 5.0,
        "reward_accepted": 1.0,
        "reward_rejected": 0.0,
    },
    {
        "name": "aggressive_best",
        "reward_global_best": 20.0,
        "reward_current_improved": 5.0,
        "reward_accepted": 1.0,
        "reward_rejected": 0.0,
    },
    {
        "name": "smooth_reward",
        "reward_global_best": 8.0,
        "reward_current_improved": 4.0,
        "reward_accepted": 1.0,
        "reward_rejected": 0.0,
    },
    {
        "name": "improvement_only",
        "reward_global_best": 10.0,
        "reward_current_improved": 5.0,
        "reward_accepted": 0.0,
        "reward_rejected": 0.0,
    },
    {
        "name": "exploration_friendly",
        "reward_global_best": 10.0,
        "reward_current_improved": 5.0,
        "reward_accepted": 2.0,
        "reward_rejected": 0.0,
    },
]

PRESET_INSTANCES = {
    "smoke": [
        "data/generated/uniform/uniform_center_n100_k5_seed01.txt",
    ],
    "n100": [
        "data/generated/uniform/uniform_center_n100_k5_seed01.txt",
        "data/generated/cluster/cluster5_n100_k5_seed01.txt",
        "data/generated/outlier/outlier10pct_n100_k5_seed01.txt",
        "data/generated/corridor/corridor_edge_n100_k5_seed01.txt",
    ],
    "n1000": [
        "data/generated/uniform/uniform_center_n1000_k100_seed01.txt",
        "data/generated/cluster/cluster20_n1000_k100_seed01.txt",
        "data/generated/outlier/outlier5pct_n1000_k100_seed01.txt",
        "data/generated/corridor/corridor_edge_n1000_k100_seed01.txt",
    ],
    "recommended": [
        "data/generated/uniform/uniform_center_n100_k5_seed01.txt",
        "data/generated/cluster/cluster5_n100_k5_seed01.txt",
        "data/generated/outlier/outlier10pct_n100_k5_seed01.txt",
        "data/generated/corridor/corridor_edge_n100_k5_seed01.txt",
        "data/generated/uniform/uniform_center_n300_k20_seed01.txt",
        "data/generated/cluster/cluster10_n300_k20_seed01.txt",
        "data/generated/outlier/outlier10pct_n300_k20_seed01.txt",
        "data/generated/corridor/corridor_edge_n300_k20_seed01.txt",
    ],
}

BASE_DESTROY = DESTROY_CONFIGS[1]
BASE_SA = SA_CONFIGS[2]
BASE_REWARD = REWARD_CONFIGS[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=tuple(PRESET_INSTANCES),
        default="smoke",
        help="Instance preset used when --instances is omitted.",
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        help="Explicit instance paths. Overrides --preset.",
    )
    parser.add_argument(
        "--instance-file",
        help="Text file with one instance path per line. Overrides --preset.",
    )
    parser.add_argument("--seeds", default="1,2,3", help="Comma-separated random seeds.")
    parser.add_argument("--time-limit", type=float, default=3.0)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument(
        "--output-dir",
        default="output/config_tuning",
        help="Directory for CSV and JSON outputs.",
    )
    parser.add_argument(
        "--run-final-only",
        action="store_true",
        help="Skip staged tuning and only run final validation from first top-k candidates.",
    )
    parser.add_argument(
        "--rerun-final-validation",
        action="store_true",
        help="Run final configs again instead of summarizing them from reward tuning.",
    )
    return parser


def config_without_name(config: dict[str, float | str]) -> dict[str, float]:
    return {key: value for key, value in config.items() if key != "name"}


def merged_config(
    *,
    time_limit: float,
    seed: int,
    destroy: dict[str, float | str],
    sa: dict[str, float | str],
    reward: dict[str, float | str],
) -> ALNSConfig:
    values = {
        "time_limit": time_limit,
        "seed": seed,
        **config_without_name(destroy),
        **config_without_name(sa),
        **config_without_name(reward),
    }
    return ALNSConfig(**values)


def config_json(config: ALNSConfig) -> str:
    keys = [
        "q_min_ratio",
        "q_max_ratio",
        "initial_temperature",
        "cooling_rate",
        "reward_global_best",
        "reward_current_improved",
        "reward_accepted",
        "reward_rejected",
    ]
    return json.dumps({key: getattr(config, key) for key in keys}, sort_keys=True)


def load_instances(paths: Iterable[str]):
    instances = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(path)
        instances.append((path, load_instance(path)))
    return instances


def read_instance_file(path: str) -> list[str]:
    instance_paths = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        instance_paths.append(line)
    return instance_paths


def run_candidate(
    *,
    stage: str,
    config_name: str,
    destroy_name: str,
    sa_name: str,
    reward_name: str,
    destroy: dict[str, float | str],
    sa: dict[str, float | str],
    reward: dict[str, float | str],
    instances,
    seeds: list[int],
    time_limit: float,
    timestamp: str,
) -> list[dict[str, object]]:
    rows = []
    for instance_path, instance in instances:
        for seed in seeds:
            config = merged_config(
                time_limit=time_limit,
                seed=seed,
                destroy=destroy,
                sa=sa,
                reward=reward,
            )
            result = ALNSSolver(config).solve(instance)
            objective = result.best.evaluate(instance)
            rows.append(
                {
                    "timestamp": timestamp,
                    "stage": stage,
                    "config_name": config_name,
                    "destroy_name": destroy_name,
                    "sa_name": sa_name,
                    "reward_name": reward_name,
                    "instance": instance_path.as_posix(),
                    "n": instance.n,
                    "k": instance.k,
                    "seed": seed,
                    "time_limit": time_limit,
                    "config_json": config_json(config),
                    "feasible": result.best.is_feasible(instance),
                    "max_route": objective.max_route_length,
                    "total_distance": objective.total_distance,
                    "balance": objective.balance,
                    "runtime": result.runtime,
                    "iterations": result.iterations,
                    "destroy_weights": json.dumps(result.destroy_weights, sort_keys=True),
                    "repair_weights": json.dumps(result.repair_weights, sort_keys=True),
                }
            )
    return rows


def baseline_lookup(baseline_rows: list[dict[str, object]]) -> dict[tuple[str, int], dict[str, float]]:
    lookup = {}
    for row in baseline_rows:
        key = (str(row["instance"]), int(row["seed"]))
        lookup[key] = {
            "max_route": float(row["max_route"]),
            "total_distance": float(row["total_distance"]),
        }
    return lookup


def add_relative_metrics(
    rows: list[dict[str, object]],
    baselines: dict[tuple[str, int], dict[str, float]],
) -> None:
    for row in rows:
        key = (str(row["instance"]), int(row["seed"]))
        baseline = baselines[key]
        baseline_max_route = baseline["max_route"]
        baseline_total_distance = baseline["total_distance"]
        max_route = float(row["max_route"])
        total_distance = float(row["total_distance"])

        row["baseline_max_route"] = baseline_max_route
        row["baseline_total_distance"] = baseline_total_distance
        row["relative_max_route"] = max_route / baseline_max_route
        row["relative_total_distance"] = total_distance / baseline_total_distance
        row["max_route_improvement_pct"] = (
            (baseline_max_route - max_route) / baseline_max_route
        ) * 100.0
        row["total_distance_improvement_pct"] = (
            (baseline_total_distance - total_distance) / baseline_total_distance
        ) * 100.0


def aggregate(rows: list[dict[str, object]], key_field: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key_field])].append(row)

    summaries = []
    for key, group in grouped.items():
        max_routes = [float(row["max_route"]) for row in group]
        total_distances = [float(row["total_distance"]) for row in group]
        balances = [float(row["balance"]) for row in group]
        runtimes = [float(row["runtime"]) for row in group]
        iterations = [int(row["iterations"]) for row in group]
        relative_max_routes = [float(row["relative_max_route"]) for row in group]
        max_route_improvements = [float(row["max_route_improvement_pct"]) for row in group]
        summaries.append(
            {
                "group_key": key,
                "runs": len(group),
                "mean_relative_max_route": statistics.mean(relative_max_routes),
                "mean_max_route_improvement_pct": statistics.mean(max_route_improvements),
                "median_max_route_improvement_pct": statistics.median(max_route_improvements),
                "win_rate": sum(1 for value in relative_max_routes if value < 1.0)
                / len(relative_max_routes),
                "mean_max_route": statistics.mean(max_routes),
                "mean_total_distance": statistics.mean(total_distances),
                "mean_balance": statistics.mean(balances),
                "mean_runtime": statistics.mean(runtimes),
                "mean_iterations": statistics.mean(iterations),
                "best_max_route": min(max_routes),
                "worst_max_route": max(max_routes),
            }
        )
    summaries.sort(
        key=lambda row: (
            row["mean_relative_max_route"],
            row["mean_max_route"],
            row["mean_total_distance"],
        )
    )
    return summaries


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def select_configs(candidates: list[dict[str, float | str]], summaries, top_k: int):
    by_name = {str(candidate["name"]): candidate for candidate in candidates}
    selected = []
    for summary in summaries[:top_k]:
        selected.append(by_name[str(summary["group_key"])])
    return selected


def print_summary(title: str, summaries: list[dict[str, object]], top_k: int) -> None:
    print(f"\n{title}")
    for rank, row in enumerate(summaries[:top_k], start=1):
        print(
            f"{rank}. {row['group_key']}: "
            f"mean_relative={float(row['mean_relative_max_route']):.5f}, "
            f"improvement={float(row['mean_max_route_improvement_pct']):.3f}%, "
            f"mean_total={float(row['mean_total_distance']):.3f}, "
            f"runs={row['runs']}"
        )


def selection_rows(
    *,
    section: str,
    summaries: list[dict[str, object]],
    limit: int,
    note: str,
) -> list[dict[str, object]]:
    rows = []
    for rank, row in enumerate(summaries[:limit], start=1):
        rows.append(
            {
                "section": section,
                "rank": rank,
                "group_key": row["group_key"],
                "runs": row["runs"],
                "mean_relative_max_route": row["mean_relative_max_route"],
                "win_rate": row["win_rate"],
                "mean_max_route_improvement_pct": row["mean_max_route_improvement_pct"],
                "median_max_route_improvement_pct": row[
                    "median_max_route_improvement_pct"
                ],
                "mean_max_route": row["mean_max_route"],
                "mean_total_distance": row["mean_total_distance"],
                "stage": row["stage"],
                "note": note,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
    if args.instance_file:
        instance_paths = read_instance_file(args.instance_file)
    else:
        instance_paths = args.instances or PRESET_INSTANCES[args.preset]
    instances = load_instances(instance_paths)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir)

    all_rows: list[dict[str, object]] = []
    all_summaries: list[dict[str, object]] = []
    selected_rows: list[dict[str, object]] = []
    reward_rows: list[dict[str, object]] = []

    print(f"Loaded {len(instances)} instance(s), seeds={seeds}, time_limit={args.time_limit}s")

    baseline_rows = run_candidate(
        stage="baseline",
        config_name="baseline",
        destroy_name=str(BASE_DESTROY["name"]),
        sa_name=str(BASE_SA["name"]),
        reward_name=str(BASE_REWARD["name"]),
        destroy=BASE_DESTROY,
        sa=BASE_SA,
        reward=BASE_REWARD,
        instances=instances,
        seeds=seeds,
        time_limit=args.time_limit,
        timestamp=timestamp,
    )
    baselines = baseline_lookup(baseline_rows)
    add_relative_metrics(baseline_rows, baselines)
    all_rows.extend(baseline_rows)
    baseline_summary = aggregate(baseline_rows, "config_name")
    for row in baseline_summary:
        row["stage"] = "baseline"
    all_summaries.extend(baseline_summary)
    print_summary("Baseline", baseline_summary, args.top_k)

    if args.run_final_only:
        top_destroy = DESTROY_CONFIGS[: args.top_k]
        top_sa = SA_CONFIGS[: args.top_k]
        top_reward = REWARD_CONFIGS[: args.top_k]
    else:
        destroy_rows = []
        for destroy in DESTROY_CONFIGS:
            destroy_rows.extend(
                run_candidate(
                    stage="destroy_tuning",
                    config_name=str(destroy["name"]),
                    destroy_name=str(destroy["name"]),
                    sa_name=str(BASE_SA["name"]),
                    reward_name=str(BASE_REWARD["name"]),
                    destroy=destroy,
                    sa=BASE_SA,
                    reward=BASE_REWARD,
                    instances=instances,
                    seeds=seeds,
                    time_limit=args.time_limit,
                    timestamp=timestamp,
                )
            )
        add_relative_metrics(destroy_rows, baselines)
        all_rows.extend(destroy_rows)
        destroy_summary = aggregate(destroy_rows, "destroy_name")
        for row in destroy_summary:
            row["stage"] = "destroy_tuning"
        all_summaries.extend(destroy_summary)
        print_summary("Destroy tuning", destroy_summary, args.top_k)
        top_destroy = select_configs(DESTROY_CONFIGS, destroy_summary, args.top_k)
        selected_rows.extend(
            selection_rows(
                section=f"destroy_top{args.top_k}",
                summaries=destroy_summary,
                limit=args.top_k,
                note="selected_destroy",
            )
        )

        sa_rows = []
        for destroy in top_destroy:
            for sa in SA_CONFIGS:
                name = f"{destroy['name']}__{sa['name']}"
                sa_rows.extend(
                    run_candidate(
                        stage="sa_tuning",
                        config_name=name,
                        destroy_name=str(destroy["name"]),
                        sa_name=str(sa["name"]),
                        reward_name=str(BASE_REWARD["name"]),
                        destroy=destroy,
                        sa=sa,
                        reward=BASE_REWARD,
                        instances=instances,
                        seeds=seeds,
                        time_limit=args.time_limit,
                        timestamp=timestamp,
                    )
                )
        add_relative_metrics(sa_rows, baselines)
        all_rows.extend(sa_rows)
        sa_summary = aggregate(sa_rows, "sa_name")
        for row in sa_summary:
            row["stage"] = "sa_tuning"
        all_summaries.extend(sa_summary)
        print_summary("SA tuning", sa_summary, args.top_k)
        top_sa = select_configs(SA_CONFIGS, sa_summary, args.top_k)
        selected_rows.extend(
            selection_rows(
                section=f"sa_top{args.top_k}",
                summaries=sa_summary,
                limit=args.top_k,
                note="selected_sa",
            )
        )

        for destroy in top_destroy:
            for sa in top_sa:
                for reward in REWARD_CONFIGS:
                    name = f"{destroy['name']}__{sa['name']}__{reward['name']}"
                    reward_rows.extend(
                        run_candidate(
                            stage="reward_tuning",
                            config_name=name,
                            destroy_name=str(destroy["name"]),
                            sa_name=str(sa["name"]),
                            reward_name=str(reward["name"]),
                            destroy=destroy,
                            sa=sa,
                            reward=reward,
                            instances=instances,
                            seeds=seeds,
                            time_limit=args.time_limit,
                            timestamp=timestamp,
                        )
                    )
        add_relative_metrics(reward_rows, baselines)
        all_rows.extend(reward_rows)
        reward_summary = aggregate(reward_rows, "reward_name")
        for row in reward_summary:
            row["stage"] = "reward_tuning"
        all_summaries.extend(reward_summary)
        print_summary("Reward tuning", reward_summary, args.top_k)
        top_reward = select_configs(REWARD_CONFIGS, reward_summary, args.top_k)
        selected_rows.extend(
            selection_rows(
                section=f"reward_top{args.top_k}",
                summaries=reward_summary,
                limit=args.top_k,
                note="selected_reward",
            )
        )

    final_stage = "final_selection"
    if args.run_final_only or args.rerun_final_validation:
        final_stage = "final_validation"
        final_rows = []
        for destroy in top_destroy:
            for sa in top_sa:
                for reward in top_reward:
                    name = f"{destroy['name']}__{sa['name']}__{reward['name']}"
                    final_rows.extend(
                        run_candidate(
                            stage=final_stage,
                            config_name=name,
                            destroy_name=str(destroy["name"]),
                            sa_name=str(sa["name"]),
                            reward_name=str(reward["name"]),
                            destroy=destroy,
                            sa=sa,
                            reward=reward,
                            instances=instances,
                            seeds=seeds,
                            time_limit=args.time_limit,
                            timestamp=timestamp,
                        )
                    )
        add_relative_metrics(final_rows, baselines)
        all_rows.extend(final_rows)
    else:
        selected_reward_names = {str(reward["name"]) for reward in top_reward}
        final_rows = [
            row for row in reward_rows if str(row["reward_name"]) in selected_reward_names
        ]
    final_summary = aggregate(final_rows, "config_name")
    for row in final_summary:
        row["stage"] = final_stage
    all_summaries.extend(final_summary)
    print_summary(final_stage.replace("_", " ").title(), final_summary, args.top_k)
    final_limit = len(top_destroy) * len(top_sa) * len(top_reward)
    selected_rows.extend(
        selection_rows(
            section=f"final_top{final_limit}",
            summaries=final_summary,
            limit=final_limit,
            note="final_candidate",
        )
    )
    selected_rows.extend(
        selection_rows(
            section="final_choice",
            summaries=final_summary,
            limit=1,
            note="chosen_config",
        )
    )

    rows_path = output_dir / f"{timestamp}_alns_tuning_runs.csv"
    summary_path = output_dir / f"{timestamp}_alns_tuning_summary.csv"
    selection_path = output_dir / f"{timestamp}_alns_tuning_selection.csv"
    meta_path = output_dir / f"{timestamp}_alns_tuning_meta.json"
    write_csv(rows_path, all_rows)
    write_csv(summary_path, all_summaries)
    write_csv(selection_path, selected_rows)
    meta_path.write_text(
        json.dumps(
            {
                "preset": args.preset,
                "instances": [path.as_posix() for path, _ in instances],
                "seeds": seeds,
                "time_limit": args.time_limit,
                "top_k": args.top_k,
                "destroy_configs": DESTROY_CONFIGS,
                "sa_configs": SA_CONFIGS,
                "reward_configs": REWARD_CONFIGS,
                "evaluation_protocol": {
                    "baseline_key": "same instance + same solver seed",
                    "primary_metric": "mean_relative_max_route",
                    "relative_max_route": "config_max_route / baseline_max_route",
                    "max_route_improvement_pct": (
                        "100 * (baseline_max_route - config_max_route) "
                        "/ baseline_max_route"
                    ),
                    "win_rate": "share of runs where config max_route < baseline max_route",
                    "ranking_order": [
                        "lower mean_relative_max_route",
                        "higher win_rate",
                        "higher mean_max_route_improvement_pct",
                        "higher median_max_route_improvement_pct",
                        "lower mean_total_distance",
                    ],
                },
                "selected_destroy": [config_without_name(destroy) for destroy in top_destroy],
                "selected_sa": [config_without_name(sa) for sa in top_sa],
                "selected_reward": [config_without_name(reward) for reward in top_reward],
                "final_stage": final_stage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nWrote runs: {rows_path}")
    print(f"Wrote summary: {summary_path}")
    print(f"Wrote selection: {selection_path}")
    print(f"Wrote meta: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
