from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from heapq import nsmallest
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Instance:
    """Min-Max VRP instance.

    Nodes are numbered 0..n. Node 0 is the depot. A route is represented as
    [0, customer_1, customer_2, ...]. By default, the route does NOT return to
    depot because the project statement's output format only requires x[1] = 0.
    Set return_to_depot=True when evaluating closed VRP tours.

    The instance also keeps a small nearest-neighbor cache. This is important for
    fast ALNS repair operators: instead of testing every possible insertion
    position, we can prioritize routes and positions that contain nearby nodes.
    """

    n: int
    k: int
    distance: tuple[tuple[float, ...], ...]
    return_to_depot: bool = False
    _nearest_cache: dict[tuple[int, int], tuple[int, ...]] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_distance_matrix(
        cls, matrix: Sequence[Sequence[float]], k: int, return_to_depot: bool = False
    ) -> "Instance":
        size = len(matrix)
        if size == 0 or any(len(row) != size for row in matrix):
            raise ValueError("Distance matrix must be square.")
        if k <= 0:
            raise ValueError("K must be positive.")
        return cls(size - 1, k, tuple(tuple(float(x) for x in row) for row in matrix), return_to_depot)

    @classmethod
    def from_coordinates(
        cls, coords: Sequence[Sequence[float]], k: int, return_to_depot: bool = False
    ) -> "Instance":
        if not coords:
            raise ValueError("Coordinate list is empty.")
        points = [(float(c[0]), float(c[1])) for c in coords]
        matrix: list[list[float]] = []
        for xi, yi in points:
            row = []
            for xj, yj in points:
                row.append(hypot(xi - xj, yi - yj))
            matrix.append(row)
        return cls.from_distance_matrix(matrix, k, return_to_depot)

    @classmethod
    def from_file(cls, path: str | Path, return_to_depot: bool = False) -> "Instance":
        """Read either project distance-matrix input or coordinate input.

        Supported formats:
        1) N K followed by N+1 rows, each with N+1 distances.
        2) N K followed by N+1 rows, each with 2 coordinates: x y.
        """
        text = Path(path).read_text(encoding="utf-8").strip().splitlines()
        if not text:
            raise ValueError("Input file is empty.")
        n, k = map(int, text[0].split()[:2])
        rows = [[float(x) for x in line.split()] for line in text[1:] if line.strip()]
        if len(rows) != n + 1:
            raise ValueError(f"Expected {n + 1} data rows after first line, got {len(rows)}.")
        if all(len(row) == n + 1 for row in rows):
            return cls.from_distance_matrix(rows, k, return_to_depot)
        if all(len(row) >= 2 for row in rows):
            return cls.from_coordinates([row[:2] for row in rows], k, return_to_depot)
        raise ValueError("Unknown input format: expected distance matrix or coordinates.")

    def d(self, i: int, j: int) -> float:
        return self.distance[i][j]

    def nearest_customers(self, customer: int, limit: int = 32) -> tuple[int, ...]:
        """Return nearest pickup points to ``customer``; depot is excluded.

        Only the requested prefix is computed with ``heapq.nsmallest`` and then
        cached. This is much cheaper than sorting all N customers during every
        repair step on large instances.
        """
        key = (customer, limit)
        if key not in self._nearest_cache:
            self._nearest_cache[key] = tuple(
                nsmallest(limit, (j for j in range(1, self.n + 1) if j != customer), key=lambda j: self.distance[customer][j])
            )
        return self._nearest_cache[key]

