"""Convert the curated report benchmark set from raw data.

This script is intentionally presentation-friendly: every converted file in
``data/tsplib_converted``, ``data/cvrplib_converted`` and
``data/mtsplib_minmax`` can be traced back to raw files under ``data/raw``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from benchmark_data_utils import build_distance_matrix, parse_vrplib_text, write_project_instance


TSPLIB_SELECTION = {
    "eil51": [2],
    "berlin52": [3],
    "kroA100": [5],
    "ch130": [10],
    "kroA200": [20],
    "lin318": [20],
    "pcb442": [50],
    "u724": [100],
}

CVRPLIB_SELECTION = {
    "A-n32-k5": 5,
    "A-n60-k9": 9,
    "A-n80-k10": 10,
    "P-n101-k4": 4,
    "M-n151-k12": 12,
    "X-n251-k28": 28,
    "X-n459-k26": 26,
    "X-n749-k98": 98,
    "X-n1001-k43": 43,
}

MTSPLIB_SELECTION = {
    "eil51": [2, 3, 5, 7],
    "berlin52": [2, 3, 5, 7],
    "eil76": [2, 3, 5, 7],
    "rat99": [2, 3, 5, 7],
}


def clear_txt_files(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for txt_file in path.glob("*.txt"):
        txt_file.unlink()


def convert_tsp_file(raw_path: Path, output_path: Path, k: int) -> None:
    instance = parse_vrplib_text(raw_path.read_text(encoding="utf-8", errors="replace"), raw_path.stem)
    distance = build_distance_matrix(instance)
    write_project_instance(output_path, distance, k)


def install_tsplib() -> int:
    raw_dir = Path("data/raw/tsplib")
    output_dir = Path("data/tsplib_converted")
    clear_txt_files(output_dir)

    count = 0
    for name, k_values in TSPLIB_SELECTION.items():
        raw_path = raw_dir / f"{name}.tsp"
        if not raw_path.exists():
            raise FileNotFoundError(f"missing raw TSPLIB file: {raw_path}")
        for k in k_values:
            convert_tsp_file(raw_path, output_dir / f"{name}_k{k}.txt", k)
            count += 1
    return count


def install_cvrplib() -> int:
    raw_dir = Path("data/raw/cvrplib")
    output_dir = Path("data/cvrplib_converted")
    clear_txt_files(output_dir)

    count = 0
    for name, k in CVRPLIB_SELECTION.items():
        raw_path = raw_dir / f"{name}.vrp"
        if not raw_path.exists():
            raise FileNotFoundError(f"missing raw CVRPLIB file: {raw_path}")
        instance = parse_vrplib_text(raw_path.read_text(encoding="utf-8", errors="replace"), name)
        distance = build_distance_matrix(instance)
        write_project_instance(output_dir / f"{name}.txt", distance, k)
        count += 1
    return count


def install_mtsplib() -> int:
    raw_dir = Path("data/raw/mtsplib_minmax/tsp")
    output_dir = Path("data/mtsplib_minmax")
    output_dir.mkdir(parents=True, exist_ok=True)

    for txt_file in output_dir.glob("*.txt"):
        txt_file.unlink()

    count = 0
    for name, k_values in MTSPLIB_SELECTION.items():
        raw_path = raw_dir / f"{name}.tsp"
        if not raw_path.exists():
            tsplib_fallback = Path("data/raw/tsplib") / f"{name}.tsp"
            if not tsplib_fallback.exists():
                raise FileNotFoundError(f"missing raw MTSPLIB source file: {raw_path}")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tsplib_fallback, raw_path)
        for k in k_values:
            convert_tsp_file(raw_path, output_dir / f"{name}_k{k}.txt", k)
            count += 1
    return count


def main() -> None:
    tsplib_count = install_tsplib()
    cvrplib_count = install_cvrplib()
    mtsplib_count = install_mtsplib()
    print(f"TSPLIB converted files: {tsplib_count}")
    print(f"CVRPLIB converted files: {cvrplib_count}")
    print(f"MTSPLIB converted files: {mtsplib_count}")


if __name__ == "__main__":
    main()
