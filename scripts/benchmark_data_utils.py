"""Shared helpers for benchmark raw-data conversion."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RawInstance:
    name: str
    dimension: int
    edge_weight_type: str
    edge_weight_format: str | None
    coords: list[tuple[float, ...]]
    explicit_weights: list[int]
    depot_index: int


def parse_header_value(line: str) -> tuple[str, str] | None:
    if ":" in line:
        key, value = line.split(":", 1)
        return key.strip().upper(), value.strip()

    parts = line.split(maxsplit=1)
    if len(parts) == 2 and parts[0].isupper():
        return parts[0].upper(), parts[1].strip()
    return None


def parse_vrplib_text(text: str, fallback_name: str) -> RawInstance:
    headers: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper() == "EOF":
            break

        upper = line.upper().rstrip(":")
        if upper.endswith("_SECTION"):
            section = upper
            sections[section] = []
            continue

        if section is not None:
            sections[section].append(line)
            continue

        header = parse_header_value(line)
        if header is not None:
            key, value = header
            headers[key] = value

    coords: list[tuple[float, ...]] = []
    for line in sections.get("NODE_COORD_SECTION", []):
        parts = line.split()
        if len(parts) >= 3:
            coords.append(tuple(float(part) for part in parts[1:]))

    explicit_weights: list[int] = []
    for line in sections.get("EDGE_WEIGHT_SECTION", []):
        explicit_weights.extend(int(float(token)) for token in line.split())

    depot_index = 1
    for line in sections.get("DEPOT_SECTION", []):
        token = line.split()[0]
        if token == "-1":
            break
        depot_index = int(token)
        break

    dimension = int(headers.get("DIMENSION", "0")) or len(coords)
    edge_weight_type = headers.get("EDGE_WEIGHT_TYPE", "EUC_2D").upper()
    edge_weight_format = headers.get("EDGE_WEIGHT_FORMAT")

    return RawInstance(
        name=headers.get("NAME", fallback_name),
        dimension=dimension,
        edge_weight_type=edge_weight_type,
        edge_weight_format=edge_weight_format.upper() if edge_weight_format else None,
        coords=coords,
        explicit_weights=explicit_weights,
        depot_index=depot_index,
    )


def tsplib_nint(value: float) -> int:
    """TSPLIB nearest-integer rule used by EUC_2D."""
    return int(value + 0.5)


def geo_to_radians(value: float) -> float:
    degrees = int(value)
    minutes = value - degrees
    return math.pi * (degrees + 5.0 * minutes / 3.0) / 180.0


def geo_distance(a: tuple[float, ...], b: tuple[float, ...]) -> int:
    radius = 6378.388
    lat_a = geo_to_radians(a[0])
    lon_a = geo_to_radians(a[1])
    lat_b = geo_to_radians(b[0])
    lon_b = geo_to_radians(b[1])
    q1 = math.cos(lon_a - lon_b)
    q2 = math.cos(lat_a - lat_b)
    q3 = math.cos(lat_a + lat_b)
    return int(radius * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)


def coord_distance(a: tuple[float, ...], b: tuple[float, ...], edge_weight_type: str) -> int:
    if edge_weight_type == "EUC_2D":
        return tsplib_nint(math.dist(a[:2], b[:2]))
    if edge_weight_type == "CEIL_2D":
        return math.ceil(math.dist(a[:2], b[:2]))
    if edge_weight_type == "ATT":
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        rij = math.sqrt((dx * dx + dy * dy) / 10.0)
        tij = tsplib_nint(rij)
        return tij if tij >= rij else tij + 1
    if edge_weight_type == "GEO":
        return geo_distance(a, b)
    raise ValueError(f"unsupported EDGE_WEIGHT_TYPE={edge_weight_type}")


def build_explicit_matrix(instance: RawInstance) -> list[list[int]]:
    n = instance.dimension
    fmt = instance.edge_weight_format
    values = instance.explicit_weights
    matrix = [[0 for _ in range(n)] for _ in range(n)]

    if fmt == "FULL_MATRIX":
        if len(values) < n * n:
            raise ValueError("EDGE_WEIGHT_SECTION shorter than DIMENSION^2")
        for i in range(n):
            for j in range(n):
                matrix[i][j] = values[i * n + j]
        return matrix

    index = 0
    if fmt == "LOWER_DIAG_ROW":
        for i in range(n):
            for j in range(i + 1):
                matrix[i][j] = matrix[j][i] = values[index]
                index += 1
        return matrix

    if fmt == "UPPER_DIAG_ROW":
        for i in range(n):
            for j in range(i, n):
                matrix[i][j] = matrix[j][i] = values[index]
                index += 1
        return matrix

    if fmt == "LOWER_ROW":
        for i in range(1, n):
            for j in range(i):
                matrix[i][j] = matrix[j][i] = values[index]
                index += 1
        return matrix

    if fmt == "UPPER_ROW":
        for i in range(n - 1):
            for j in range(i + 1, n):
                matrix[i][j] = matrix[j][i] = values[index]
                index += 1
        return matrix

    raise ValueError(f"unsupported EDGE_WEIGHT_FORMAT={fmt}")


def build_distance_matrix(instance: RawInstance) -> list[list[int]]:
    if instance.edge_weight_type == "EXPLICIT":
        matrix = build_explicit_matrix(instance)
    else:
        if len(instance.coords) != instance.dimension:
            raise ValueError("NODE_COORD_SECTION length does not match DIMENSION")
        matrix = [
            [coord_distance(a, b, instance.edge_weight_type) for b in instance.coords]
            for a in instance.coords
        ]

    depot = instance.depot_index - 1
    order = [depot] + [idx for idx in range(instance.dimension) if idx != depot]
    return [[matrix[i][j] for j in order] for i in order]


def write_project_instance(path, distance: list[list[int]], k: int) -> None:
    n = len(distance) - 1
    lines = [f"{n} {k}"]
    lines.extend(" ".join(str(value) for value in row) for row in distance)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
