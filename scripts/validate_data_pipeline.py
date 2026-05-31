"""Validate raw-to-converted data and reference files."""

from __future__ import annotations

import csv
from pathlib import Path

from benchmark_data_utils import build_distance_matrix, parse_vrplib_text
from install_report_benchmarks import CVRPLIB_SELECTION, MTSPLIB_SELECTION, TSPLIB_SELECTION
from minmax_vrp.io import read_instance


def assert_distance_matches(raw_path: Path, converted_path: Path) -> tuple[int, int]:
    raw = parse_vrplib_text(raw_path.read_text(encoding="utf-8", errors="replace"), raw_path.stem)
    expected = build_distance_matrix(raw)
    converted = read_instance(converted_path)
    if converted.distance != expected:
        raise AssertionError(f"distance matrix mismatch: {raw_path} -> {converted_path}")
    return converted.n, converted.k


def validate_tsplib() -> list[dict[str, object]]:
    rows = []
    for name, k_values in TSPLIB_SELECTION.items():
        for k in k_values:
            converted_path = Path("data/tsplib_converted") / f"{name}_k{k}.txt"
            n, actual_k = assert_distance_matches(Path("data/raw/tsplib") / f"{name}.tsp", converted_path)
            rows.append({"dataset": "tsplib_converted", "file": converted_path.name, "n": n, "k": actual_k})
    return rows


def validate_cvrplib() -> list[dict[str, object]]:
    rows = []
    for name, k in CVRPLIB_SELECTION.items():
        converted_path = Path("data/cvrplib_converted") / f"{name}.txt"
        n, actual_k = assert_distance_matches(Path("data/raw/cvrplib") / f"{name}.vrp", converted_path)
        if actual_k != k:
            raise AssertionError(f"K mismatch for {converted_path}: {actual_k} != {k}")
        rows.append({"dataset": "cvrplib_converted", "file": converted_path.name, "n": n, "k": actual_k})
    return rows


def validate_mtsplib() -> list[dict[str, object]]:
    rows = []
    for name, k_values in MTSPLIB_SELECTION.items():
        for k in k_values:
            converted_path = Path("data/mtsplib_minmax") / f"{name}_k{k}.txt"
            n, actual_k = assert_distance_matches(
                Path("data/raw/mtsplib_minmax/tsp") / f"{name}.tsp",
                converted_path,
            )
            rows.append({"dataset": "mtsplib_minmax", "file": converted_path.name, "n": n, "k": actual_k})
    return rows


def validate_hustack() -> list[dict[str, object]]:
    rows = []
    for path in sorted(Path("data/hustack").glob("tc*.txt"), key=lambda p: p.stem):
        instance = read_instance(path)
        rows.append({"dataset": "hustack", "file": path.name, "n": instance.n, "k": instance.k})
    return rows


def validate_reference(path: Path, expected_rows: int) -> None:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != expected_rows:
        raise AssertionError(f"{path} has {len(rows)} rows, expected {expected_rows}")
    for row in rows:
        int(row["objective_max_route"])
        int(row["total_distance"])
        int(row["amplitude"])
        int(row["route_count"])


def main() -> None:
    rows = []
    rows.extend(validate_tsplib())
    rows.extend(validate_cvrplib())
    rows.extend(validate_mtsplib())
    rows.extend(validate_hustack())

    validate_reference(Path("data/hustack/reference.csv"), 13)
    validate_reference(Path("data/mtsplib_minmax/reference.csv"), 16)

    output_path = Path("data/validation_summary.csv")
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["dataset", "file", "n", "k"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Validated {len(rows)} converted/input files.")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
