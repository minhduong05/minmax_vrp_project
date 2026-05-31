"""Download MTSPLIB MinMax tour files and build integer-distance references.

The MTSPLIB web page reports CPLEX tour costs as floating-point Euclidean
lengths. This script downloads the published tours and re-evaluates them on the
project's converted integer distance matrices in ``data/mtsplib_minmax``.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

from minmax_vrp.io import read_instance


BASE_URL = "https://profs.info.uaic.ro/mihaela.breaban/mtsplib/MinMaxMTSP/"
INDEX_URL = urljoin(BASE_URL, "index.html")
DATA_DIR = Path("data/mtsplib_minmax")
RAW_TOUR_DIR = Path("data/raw/mtsplib_minmax/tours")
OUTPUT_PATH = DATA_DIR / "reference.csv"
ALL_OUTPUT_PATH = DATA_DIR / "reference_all.csv"


@dataclass(frozen=True)
class TourFile:
    url: str
    file_name: str
    instance: str
    k: int
    variant: str
    note: str


def fetch_text(url: str, timeout: int = 60) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_tour_files() -> list[TourFile]:
    html = fetch_text(INDEX_URL)
    hrefs = re.findall(r'href="([^"]*tours[^"]*\.txt)"', html)
    files: list[TourFile] = []

    for href in hrefs:
        file_name = Path(href).name
        match = re.match(r"(?P<instance>[A-Za-z0-9]+)\(m=(?P<k>\d+)\)-tours(?P<star>_?)\.txt", file_name)
        if match is None:
            continue

        instance = match.group("instance")
        k = int(match.group("k"))
        is_starred = bool(match.group("star"))
        files.append(
            TourFile(
                url=urljoin(BASE_URL, href),
                file_name=file_name,
                instance=instance,
                k=k,
                variant="starred" if is_starred else "main",
                note="starred CPLEX tour" if is_starred else "main CPLEX tour",
            )
        )

    return files


def download_tour_file(tour_file: TourFile) -> Path:
    RAW_TOUR_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_TOUR_DIR / tour_file.file_name
    if not target.exists():
        target.write_text(fetch_text(tour_file.url), encoding="utf-8")
    return target


def parse_tours(path: Path) -> tuple[list[list[int]], list[float]]:
    routes: list[list[int]] = []
    source_costs: list[float] = []
    pattern = re.compile(r"^(?P<route>(?:\d+\s+)+)\(#\d+\)\s+Cost:\s+(?P<cost>[-+0-9.eE]+)")

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        match = pattern.search(line)
        if match is None:
            continue

        tsp_nodes = [int(token) for token in match.group("route").split()]
        if len(tsp_nodes) < 2 or tsp_nodes[0] != 1 or tsp_nodes[-1] != 1:
            raise ValueError(f"tour must start and end at TSPLIB depot node 1: {path.name}")

        # TSPLIB node 1 is project depot 0. Nodes 2..D become project 1..D-1.
        routes.append([node - 1 for node in tsp_nodes])
        source_costs.append(float(match.group("cost")))

    if not routes:
        raise ValueError(f"no tours found in {path}")
    return routes, source_costs


def route_length(route: list[int], distance: list[list[int]]) -> int:
    return sum(distance[a][b] for a, b in zip(route, route[1:]))


def validate_routes(routes: list[list[int]], n: int, k: int) -> None:
    if len(routes) != k:
        raise ValueError(f"expected {k} routes, got {len(routes)}")

    customers = [node for route in routes for node in route[1:-1]]
    expected = set(range(1, n + 1))
    actual = set(customers)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"customer mismatch: missing={missing[:10]}, extra={extra[:10]}")
    if len(customers) != len(actual):
        raise ValueError("duplicate customer in tours")


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tour_file in discover_tour_files():
        input_path = DATA_DIR / f"{tour_file.instance}_k{tour_file.k}.txt"
        if not input_path.exists():
            continue

        local_tour_path = download_tour_file(tour_file)
        instance = read_instance(input_path)
        routes, source_costs = parse_tours(local_tour_path)
        validate_routes(routes, instance.n, instance.k)
        integer_lengths = [route_length(route, instance.distance) for route in routes]

        rows.append(
            {
                "instance": tour_file.instance,
                "n": instance.n,
                "k": tour_file.k,
                "reference_type": tour_file.variant,
                "objective_max_route": max(integer_lengths),
                "total_distance": sum(integer_lengths),
                "amplitude": max(integer_lengths) - min(integer_lengths),
                "route_count": len(routes),
                "route_lengths": " ".join(str(value) for value in integer_lengths),
                "return_to_depot": "yes",
                "source": "MTSPLIB MinMaxMTSP tours",
                "source_file": tour_file.file_name,
                "source_max_route": f"{max(source_costs):.2f}",
                "source_total_cost": f"{sum(source_costs):.2f}",
                "note": f"{tour_file.note}; objective re-evaluated on integer matrix",
            }
        )

    rows.sort(key=lambda row: (str(row["instance"]), int(row["k"]), str(row["reference_type"])))
    return rows


def main() -> None:
    rows = build_rows()
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

    with ALL_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    main_rows = [row for row in rows if row["reference_type"] == "main"]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(main_rows)

    print(f"Wrote {len(main_rows)} main rows to {OUTPUT_PATH}")
    print(f"Wrote {len(rows)} all rows to {ALL_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
