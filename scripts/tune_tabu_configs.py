from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# --- cho phep import package khi chay tu thu muc goc ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser import load_instance
from minmax_vrp.models import Solution
from minmax_vrp.algorithms.tabu_search.tabu_search import local_clear, tabu_search


# =========================== LUOI CONFIG ===========================
# Cac config can thu nghiem (tenure x max_candidates).
TENURE_VALUES = [5, 7, 10, 15]
MAX_CANDIDATES_VALUES = [100, 200, 400]

# Baseline = config goc hardcode trong main() cua tabu_search.py.
# Chay KHONG seed (deterministic) - dung lam moc so sanh.
BASELINE_TENURE = 7
BASELINE_CANDIDATES = 200

# Co bat hau toi uu 2-opt (local_clear) sau khi Tabu chay xong.
USE_LOCAL_SEARCH = True

# Quy doi time_limit -> so vong lap toi da (giong solver.py: 200 iter/giay).
ITERS_PER_SECOND = 200

# Preset instance dung khi khong truyen --instance-file / --instances.
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
}

# 16 cot dung theo output/templates/config_tuning.csv
CSV_HEADER = [
    "timestamp", "algorithm", "instance", "n", "k", "seed", "time_limit",
    "config_name", "config_json", "feasible", "max_route", "total_distance",
    "balance", "runtime", "iterations", "notes",
]
# ===================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=tuple(PRESET_INSTANCES),
        default="smoke",
        help="Bo instance dung khi khong co --instances / --instance-file.",
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        help="Danh sach duong dan instance. Ghi de --preset.",
    )
    parser.add_argument(
        "--instance-file",
        help="File text, moi dong la 1 duong dan instance. Ghi de --preset.",
    )
    parser.add_argument("--seeds", default="1,2,3", help="Cac seed, ngan cach boi dau phay.")
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--top-k", type=int, default=2, help="So config tot nhat in ra cuoi cung.")
    parser.add_argument(
        "--output-dir",
        default="output/config_tuning",
        help="Thu muc luu CSV + JSON ket qua.",
    )
    return parser


def read_instance_file(path: str) -> list[str]:
    """Doc file manifest: moi dong 1 instance, bo qua dong trong / comment."""
    out = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def resolve_instances(args) -> list[str]:
    if args.instance_file:
        return read_instance_file(args.instance_file)
    if args.instances:
        return list(args.instances)
    return list(PRESET_INSTANCES[args.preset])


def run_once(instance, tenure, max_candidates, time_limit, seed):
    """Chay Tabu mot lan voi 1 config + 1 seed, tra ve dict metric.

    tabu_search nhan seed -> moi seed cho mot quy dao tim kiem khac nhau.
    """
    n, k = instance.n, instance.k
    max_iterations = max(1, int(max(0.01, time_limit) * ITERS_PER_SECOND))

    start = time.perf_counter()
    routes, _, iterations_done = tabu_search(
        n, k, instance.distance,
        max_inter=max_iterations,
        tenure=tenure,
        max_candidates=max_candidates,
        deadline=start + max(0.0, time_limit),
        seed=seed,
    )
    if USE_LOCAL_SEARCH:
        routes = local_clear(routes, instance.distance)
    runtime = time.perf_counter() - start

    solution = Solution(routes)
    feasible = solution.is_feasible(instance)
    ev = solution.evaluate(instance)

    return {
        "feasible": feasible,
        "max_route": ev.max_route_length,
        "total_distance": ev.total_distance,
        "balance": ev.balance,
        "runtime": runtime,
        "iterations": iterations_done,
    }


def main() -> int:
    args = build_parser().parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    time_limit = args.time_limit

    instance_paths = resolve_instances(args)
    instances = []
    for raw in instance_paths:
        path = ROOT / raw if not Path(raw).is_absolute() else Path(raw)
        if not path.exists():
            raise FileNotFoundError(path)
        instances.append((Path(raw), load_instance(path)))

    output_dir = ROOT / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now():%Y-%m-%d_%H%M%S}"
    csv_path = output_dir / f"{stamp}_tabu_search_grid.csv"
    timestamp = datetime.now().isoformat(timespec="seconds")

    configs = [(t, c) for t in TENURE_VALUES for c in MAX_CANDIDATES_VALUES]
    # baseline = config goc hardcode trong main(): tenure=7, cand=200, KHONG seed.
    baseline_tenure, baseline_cand = BASELINE_TENURE, BASELINE_CANDIDATES

    total_runs = len(instances) * (1 + len(configs)) * len(seeds)  # baseline + grid, moi cai x seeds
    run_idx = 0
    rows = []

    def record(inst_path, instance, tenure, max_candidates, seed, config_name, stage):
        """Chay 1 lan + ghi 1 dong vao rows. seed=None -> deterministic."""
        nonlocal run_idx
        run_idx += 1
        seed_label = "none" if seed is None else seed
        print(f"[{run_idx}/{total_runs}] {stage}:{config_name} seed={seed_label} ...",
              end=" ", flush=True)
        m = run_once(instance, tenure, max_candidates, time_limit, seed)
        print(f"max_route={m['max_route']:.2f} runtime={m['runtime']:.2f}s "
              f"feasible={'yes' if m['feasible'] else 'NO'}")
        cfg_json = json.dumps(
            {"tenure": tenure, "max_candidates": max_candidates,
             "use_local_search": USE_LOCAL_SEARCH},
            sort_keys=True, separators=(",", ":"),
        )
        rows.append({
            "timestamp": timestamp,
            "algorithm": "tabu_search",
            "instance": inst_path.as_posix(),
            "n": instance.n,
            "k": instance.k,
            "seed": "" if seed is None else seed,
            "time_limit": time_limit,
            "config_name": config_name,
            "config_json": cfg_json,
            "feasible": "yes" if m["feasible"] else "no",
            "max_route": f"{m['max_route']:.4f}",
            "total_distance": f"{m['total_distance']:.4f}",
            "balance": f"{m['balance']:.4f}",
            "runtime": f"{m['runtime']:.4f}",
            "iterations": m["iterations"],
            "notes": stage,  # 'baseline' hoac 'grid'
        })

    for inst_path, instance in instances:
        print(f"\n=== {inst_path.as_posix()} (n={instance.n}, k={instance.k}) ===")
        # 1) Baseline: config goc, chay CUNG cac seed de ghep cap (instance, seed)
        for seed in seeds:
            record(inst_path, instance, baseline_tenure, baseline_cand,
                   seed, "baseline", "baseline")
        # 2) Luoi config: moi config x moi seed
        for tenure, max_candidates in configs:
            config_name = f"tenure{tenure}_cand{max_candidates}"
            for seed in seeds:
                record(inst_path, instance, tenure, max_candidates,
                       seed, config_name, "grid")

    # ghi CSV
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nDa ghi {len(rows)} dong vao: {csv_path}")

    # ===== TINH 4 CHI SO THEO CAP (instance + seed) =====
    # 1) Tra cuu baseline_max_route theo (instance, seed)
    baseline_lookup = {}
    for r in rows:
        if r["config_name"] == "baseline":
            key = (r["instance"], r["seed"])
            baseline_lookup[key] = float(r["max_route"])

    # 2) Voi moi config, gom cac chi so theo tung cap
    per_config = defaultdict(lambda: {
        "relative": [],        # config / baseline
        "improvement_pct": [], # 100*(baseline-config)/baseline
        "wins": 0,             # so case config < baseline
        "cases": 0,
        "raw": [],             # (instance, seed, config_v, baseline_v)
    })
    for r in rows:
        name = r["config_name"]
        if name == "baseline":
            continue
        key = (r["instance"], r["seed"])
        base_v = baseline_lookup.get(key)
        if base_v is None or base_v == 0:
            continue
        cfg_v = float(r["max_route"])
        acc = per_config[name]
        acc["relative"].append(cfg_v / base_v)
        acc["improvement_pct"].append(100.0 * (base_v - cfg_v) / base_v)
        acc["cases"] += 1
        if cfg_v < base_v:
            acc["wins"] += 1
        acc["raw"].append((r["instance"], r["seed"], cfg_v, base_v))

    # 3) Tong hop 4 chi so cho moi config
    summary = []
    for name, acc in per_config.items():
        rel = acc["relative"]
        imp = acc["improvement_pct"]
        summary.append({
            "config_name": name,
            "cases": acc["cases"],
            "mean_relative_max_route": statistics.mean(rel) if rel else float("nan"),
            "win_rate": acc["wins"] / acc["cases"] if acc["cases"] else 0.0,
            "mean_max_route_improvement_pct": statistics.mean(imp) if imp else 0.0,
            "median_max_route_improvement_pct": statistics.median(imp) if imp else 0.0,
        })
    # config tot nhat = mean_relative_max_route nho nhat (tot hon baseline nhat)
    summary.sort(key=lambda s: s["mean_relative_max_route"])

    summary_path = output_dir / f"{stamp}_tabu_search_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # ----- IN BANG 4 CHI SO -----
    print("\n" + "=" * 78)
    print("SO SANH THEO CAP (instance + seed) vs BASELINE")
    print("=" * 78)
    print(f"  {'config':<20}{'mean_rel':>10}{'win_rate':>10}"
          f"{'mean_imp%':>11}{'median_imp%':>13}")
    print("  " + "-" * 62)
    shown = summary[: args.top_k]
    for s in shown:
        print(f"  {s['config_name']:<20}"
              f"{s['mean_relative_max_route']:>10.4f}"
              f"{s['win_rate']:>10.4f}"
              f"{s['mean_max_route_improvement_pct']:>11.2f}"
              f"{s['median_max_route_improvement_pct']:>13.2f}")
    print("\n  Cach doc:")
    print("   - mean_rel  < 1.0 = tot hon baseline (cang nho cang tot). Day la chi so chinh.")
    print("   - win_rate        = ti le case config thang baseline (cang cao cang tot).")
    print("   - mean_imp%       = % cai thien trung binh (>0 tot hon).")
    print("   - median_imp%     = % cai thien o case dien hinh (it bi outlier keo).")
    print("   Neu mean_imp% cao nhung median_imp% thap => vai case cai thien manh keo mean len.")

    # ----- Bang CHI TIET THEO SEED -----
    detail = defaultdict(list)
    for r in rows:
        detail[r["config_name"]].append(
            (r["instance"], r["seed"], float(r["max_route"]))
        )

    print("\n" + "=" * 60)
    print("CHI TIET THEO SEED (tung lan chay)")
    print("=" * 60)
    order = ["baseline"] + [s["config_name"] for s in summary]
    for name in order:
        runs = detail.get(name, [])
        if not runs:
            continue
        vals = [v for (_, _, v) in runs]
        mean_v = statistics.mean(vals)
        std_v = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        print(f"\n{name}:")
        for inst, seed, v in runs:
            seed_label = "none" if seed == "" else f"seed{seed}"
            short = inst.split("/")[-1]
            print(f"    {short:<42} {seed_label:>7}: {v:>10.2f}")
        print(f"    -> mean={mean_v:.2f}  std={std_v:.2f}")

    print(f"\nTong hop day du: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())