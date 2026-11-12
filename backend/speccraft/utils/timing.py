"""High-resolution timing utilities for AST benchmark evaluation."""

from __future__ import annotations

import time
from typing import Optional


class Timer:
    """Context manager and standalone stopwatch for microsecond-precision timing."""

    def __init__(self) -> None:
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self) -> Timer:
        self.start_time = time.perf_counter()
        self.end_time = None
        return self

    def stop(self) -> float:
        if self.start_time is None:
            raise RuntimeError("Timer was never started.")
        self.end_time = time.perf_counter()
        return self.duration_ms

    @property
    def duration_ms(self) -> float:
        """Returns elapsed duration in milliseconds with two decimals."""
        if self.start_time is None:
            return 0.0
        current_or_end = self.end_time if self.end_time is not None else time.perf_counter()
        return round((current_or_end - self.start_time) * 1000.0, 2)

    def __enter__(self) -> Timer:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

