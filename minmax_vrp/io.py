from pathlib import Path

from .models import Distance, Instance, Solution


def format_distance(value: Distance) -> str:
    """Keep integer-looking values compact while preserving real distances."""
    if value == int(value):
        return str(int(value))
    return f"{value:.12g}"


def read_instance(path: str | Path) -> Instance:
    """Read the mini-project input format.

    Format:
        N K
        row 0 of distance matrix
        ...
        row N of distance matrix
    """
    tokens = Path(path).read_text(encoding="utf-8").strip().split()
    if len(tokens) < 2:
        raise ValueError("input must start with N K")
    n = int(tokens[0])
    k = int(tokens[1])
    expected = 2 + (n + 1) * (n + 1)
    if len(tokens) < expected:
        raise ValueError(f"input has {len(tokens)} tokens, expected at least {expected}")
    values: list[Distance] = []
    for token in tokens[2:expected]:
        values.append(float(token))

    distance = []
    row_size = n + 1
    for row_index in range(row_size):
        start = row_index * row_size
        end = start + row_size
        distance.append(values[start:end])
    return Instance(n=n, k=k, distance=distance)


def format_solution(solution: Solution) -> str:
    """Return the required output format.

    Line 1: K
    For each route k:
        line: lk
        line: route nodes, starting with 0
    """
    lines: list[str] = [str(len(solution.routes))]
    for route in solution.routes:
        lines.append(str(len(route)))
        lines.append(" ".join(map(str, route)))
    return "\n".join(lines)


def write_solution(solution: Solution, path: str | Path) -> None:
    Path(path).write_text(format_solution(solution) + "\n", encoding="utf-8")


def write_instance(instance: Instance, path: str | Path) -> None:
    lines = [f"{instance.n} {instance.k}"]
    lines.extend(" ".join(format_distance(value) for value in row) for row in instance.distance)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
