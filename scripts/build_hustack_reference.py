"""Build a reference CSV from HUSTACK jury outputs.

The script reads input files from ``data/hustack`` and matching jury outputs
from ``data/raw/hustack_jury``. It accepts partial data: if only ``tc1.out``
exists, only ``tc1`` is written to the reference CSV.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from minmax_vrp.io import read_instance


INPUT_DIR = Path("data/hustack")
JURY_DIR = Path("data/raw/hustack_jury")
OUTPUT_PATH = INPUT_DIR / "reference.csv"
LEGACY_OUTPUT_PATH = INPUT_DIR / "reference_jury.csv"


@dataclass(frozen=True)
class JurySolution:
    routes: list[list[int]]


def parse_jury_output(path: Path) -> JurySolution:
    tokens = path.read_text(encoding="utf-8").split()
    if not tokens:
        raise ValueError("empty output")

    cursor = 0
    route_count = int(tokens[cursor])
    cursor += 1
    routes: list[list[int]] = []

    for _ in range(route_count):
        if cursor >= len(tokens):
            raise ValueError("missing route length")
        route_len = int(tokens[cursor])
        cursor += 1

        route_tokens = tokens[cursor : cursor + route_len]
        if len(route_tokens) != route_len:
            raise ValueError("route shorter than declared length")
        cursor += route_len

        route = [int(token) for token in route_tokens]
        if not route or route[0] != 0:
            raise ValueError("each route must start at depot 0")
        routes.append(route)

    if cursor != len(tokens):
        raise ValueError("extra tokens after last route")

    return JurySolution(routes=routes)


def route_length(route: list[int], distance: list[list[int]]) -> int:
    return sum(distance[a][b] for a, b in zip(route, route[1:]))


def validate_customer_coverage(routes: list[list[int]], n: int) -> None:
    customers = [node for route in routes for node in route[1:]]
    expected = set(range(1, n + 1))
    actual = set(customers)

    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"customer mismatch: missing={missing[:10]}, extra={extra[:10]}")

    if len(customers) != len(actual):
        raise ValueError("duplicate customer in routes")


def build_reference() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    input_paths = sorted(
        INPUT_DIR.glob("tc*.txt"),
        key=lambda path: int(re.search(r"\d+", path.stem).group()),
    )
    for input_path in input_paths:
        jury_path = JURY_DIR / f"{input_path.stem}.out"
        if not jury_path.exists():
            continue

        instance = read_instance(input_path)
        solution = parse_jury_output(jury_path)
        validate_customer_coverage(solution.routes, instance.n)
        lengths = [route_length(route, instance.distance) for route in solution.routes]

        rows.append(
            {
                "instance": input_path.stem,
                "n": instance.n,
                "k": instance.k,
                "reference_type": "jury",
                "objective_max_route": max(lengths) if lengths else 0,
                "total_distance": sum(lengths),
                "amplitude": max(lengths) - min(lengths) if lengths else 0,
                "route_count": len(solution.routes),
                "route_lengths": " ".join(str(value) for value in lengths),
                "return_to_depot": "no",
                "source": "HUSTACK jury output",
                "source_file": str(jury_path.relative_to(Path("."))),
                "source_max_route": "",
                "source_total_cost": "",
                "note": "objective re-evaluated on integer input matrix",
            }
        )
    return rows


def main() -> None:
    rows = build_reference()
    fieldnames = [
        "instance",
        "n",
        "k",
        "reference_type",
        "objective_max_route",
        "total_distance",
        "amplitude",
        "route_count",
        "route_lengths",
        "return_to_depot",
        "source",
        "source_file",
        "source_max_route",
        "source_total_cost",
        "note",
    ]
    for output_path in [OUTPUT_PATH, LEGACY_OUTPUT_PATH]:
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Wrote {len(rows)} rows to {LEGACY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
