from __future__ import annotations

from pathlib import Path

from minmax_vrp.algorithms.alns.core.solution import Solution


def write_solution(solution: Solution, path: str | Path) -> None:
    Path(path).write_text(solution.to_output_text(), encoding="utf-8")

