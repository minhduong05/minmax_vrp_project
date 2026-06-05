"""Generate synthetic Min-Max VRP matrix instances under data/generated.

The output format is the project's matrix format:

    N K
    distance row 0
    ...
    distance row N

Node 0 is the depot and nodes 1..N are pickup points.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Callable


Point = tuple[float, float]
DistanceFn = Callable[[Point, Point], float]

SPACE_MIN = 0.0
SPACE_MAX = 1000.0
CENTER_DEPOT = (500.0, 500.0)
CORNER_DEPOT = (0.0, 0.0)
EDGE_DEPOT = (0.0, 500.0)


def clamp(value: float, low: float = SPACE_MIN, high: float = SPACE_MAX) -> float:
    return max(low, min(high, value))


def format_distance(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.12g}"


def euclidean(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def uniform_points(rng: random.Random, n: int) -> list[Point]:
    return [
        (rng.uniform(SPACE_MIN, SPACE_MAX), rng.uniform(SPACE_MIN, SPACE_MAX))
        for _ in range(n)
    ]


def cluster_points(rng: random.Random, n: int, cluster_count: int) -> list[Point]:
    centers = [
        (rng.uniform(120.0, 880.0), rng.uniform(120.0, 880.0))
        for _ in range(cluster_count)
    ]
    spread = 45.0 if n <= 300 else 38.0

    points: list[Point] = []
    for idx in range(n):
        center = centers[idx % cluster_count]
        points.append(
            (
                clamp(rng.gauss(center[0], spread)),
                clamp(rng.gauss(center[1], spread)),
            )
        )
    rng.shuffle(points)
    return points


def outlier_points(rng: random.Random, n: int, outlier_pct: float) -> list[Point]:
    outlier_count = max(1, round(n * outlier_pct))
    core_count = n - outlier_count

    points = [
        (
            clamp(rng.gauss(CENTER_DEPOT[0], 120.0)),
            clamp(rng.gauss(CENTER_DEPOT[1], 120.0)),
        )
        for _ in range(core_count)
    ]

    remote_boxes = [
        ((0.0, 160.0), (0.0, 160.0)),
        ((840.0, 1000.0), (0.0, 160.0)),
        ((0.0, 160.0), (840.0, 1000.0)),
        ((840.0, 1000.0), (840.0, 1000.0)),
    ]
    for idx in range(outlier_count):
        x_range, y_range = remote_boxes[idx % len(remote_boxes)]
        points.append((rng.uniform(*x_range), rng.uniform(*y_range)))

    rng.shuffle(points)
    return points


def corridor_points(rng: random.Random, n: int) -> list[Point]:
    return [
        (rng.uniform(SPACE_MIN, SPACE_MAX), clamp(rng.gauss(500.0, 12.0)))
        for _ in range(n)
    ]


def write_instance(path: Path, n: int, k: int, coords: list[Point], distance: DistanceFn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = n + 1
    if len(coords) != expected:
        raise ValueError(f"{path}: expected {expected} coordinates, got {len(coords)}")

    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(f"{n} {k}\n")
        for row_point in coords:
            row = [format_distance(distance(row_point, col_point)) for col_point in coords]
            file.write(" ".join(row))
            file.write("\n")


def seed_code(seed: int) -> str:
    return f"seed{seed:02d}"


def generate_main_group(root: Path) -> list[Path]:
    written: list[Path] = []
    sizes = [(100, 5), (300, 20), (1000, 100)]
    seeds = [1, 2, 3]

    for n, k in sizes:
        for seed in seeds:
            rng = random.Random(seed)
            filename = f"uniform_center_n{n}_k{k}_{seed_code(seed)}.txt"
            path = root / "uniform" / filename
            write_instance(path, n, k, [CENTER_DEPOT, *uniform_points(rng, n)], euclidean)
            written.append(path)

    cluster_counts = {100: 5, 300: 10, 1000: 20}
    for n, k in sizes:
        for seed in seeds:
            rng = random.Random(10_000 + seed + n)
            cluster_count = cluster_counts[n]
            filename = f"cluster{cluster_count}_n{n}_k{k}_{seed_code(seed)}.txt"
            path = root / "cluster" / filename
            write_instance(
                path,
                n,
                k,
                [CENTER_DEPOT, *cluster_points(rng, n, cluster_count)],
                euclidean,
            )
            written.append(path)

    for n, k in sizes:
        for seed in seeds:
            rng = random.Random(20_000 + seed + n)
            pct = 0.05 if n == 1000 else 0.10
            pct_label = "5pct" if pct == 0.05 else "10pct"
            filename = f"outlier{pct_label}_n{n}_k{k}_{seed_code(seed)}.txt"
            path = root / "outlier" / filename
            write_instance(path, n, k, [CENTER_DEPOT, *outlier_points(rng, n, pct)], euclidean)
            written.append(path)

    for n, k in sizes:
        for seed in seeds:
            rng = random.Random(30_000 + seed + n)
            filename = f"corridor_edge_n{n}_k{k}_{seed_code(seed)}.txt"
            path = root / "corridor" / filename
            write_instance(path, n, k, [EDGE_DEPOT, *corridor_points(rng, n)], euclidean)
            written.append(path)

    return written


def generate_k_sensitivity(root: Path) -> list[Path]:
    written: list[Path] = []

    for k in [2, 10, 50]:
        rng = random.Random(50_000 + k)
        filename = f"uniform_center_n500_k{k}_seed01.txt"
        path = root / "k_sensitivity" / filename
        write_instance(path, 500, k, [CENTER_DEPOT, *uniform_points(rng, 500)], euclidean)
        written.append(path)

    for k in [2, 10, 50]:
        rng = random.Random(60_000 + k)
        filename = f"cluster_n500_k{k}_seed01.txt"
        path = root / "k_sensitivity" / filename
        write_instance(path, 500, k, [CENTER_DEPOT, *cluster_points(rng, 500, 10)], euclidean)
        written.append(path)

    return written


def generate_depot_position(root: Path) -> list[Path]:
    written: list[Path] = []
    n = 300
    k = 20
    depots = {
        "edge": EDGE_DEPOT,
        "corner": CORNER_DEPOT,
    }

    for seed in [1, 2, 3]:
        points = uniform_points(random.Random(seed), n)
        for label, depot in depots.items():
            filename = f"uniform_{label}_n{n}_k{k}_{seed_code(seed)}.txt"
            path = root / "depot_position" / filename
            write_instance(path, n, k, [depot, *points], euclidean)
            written.append(path)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/generated"),
        help="Directory where generated instances are written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir

    written = []
    written.extend(generate_main_group(output_dir))
    written.extend(generate_k_sensitivity(output_dir))
    written.extend(generate_depot_position(output_dir))

    print(f"Generated {len(written)} files under {output_dir}")
    for path in written:
        print(path.as_posix())


if __name__ == "__main__":
    main()
