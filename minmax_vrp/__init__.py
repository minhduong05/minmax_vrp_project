"""Solvers for the Min-Max Vehicle Routing mini project."""

from .models import Instance, Solution

__all__ = [
    "ALGORITHM_NAMES",
    "ALNSConfig",
    "ALNSSolver",
    "AlgorithmConfig",
    "Instance",
    "Solution",
    "create_solver",
]


def __getattr__(name: str):
    if name in {"ALGORITHM_NAMES", "AlgorithmConfig", "create_solver"}:
        from .algorithms import ALGORITHM_NAMES, AlgorithmConfig, create_solver

        values = {
            "ALGORITHM_NAMES": ALGORITHM_NAMES,
            "AlgorithmConfig": AlgorithmConfig,
            "create_solver": create_solver,
        }
        return values[name]

    if name in {"ALNSConfig", "ALNSSolver"}:
        from .algorithms.alns import ALNSConfig, ALNSSolver

        values = {
            "ALNSConfig": ALNSConfig,
            "ALNSSolver": ALNSSolver,
        }
        return values[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
