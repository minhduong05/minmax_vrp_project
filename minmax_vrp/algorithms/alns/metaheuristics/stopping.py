from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class StopCriteria:
    max_iterations: int = 10000
    max_seconds: float | None = None
    no_improve_iterations: int | None = None
    start_time: float = field(default_factory=time.perf_counter)
    last_improve_iteration: int = 0

    def should_stop(self, iteration: int) -> bool:
        if iteration >= self.max_iterations:
            return True
        if self.max_seconds is not None and time.perf_counter() - self.start_time >= self.max_seconds:
            return True
        if self.no_improve_iterations is not None and iteration - self.last_improve_iteration >= self.no_improve_iterations:
            return True
        return False

    def mark_improvement(self, iteration: int) -> None:
        self.last_improve_iteration = iteration

