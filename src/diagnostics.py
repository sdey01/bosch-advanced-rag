"""Timing support for per-interaction pipeline diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Callable, Iterator


class InteractionTimer:
    def __init__(self, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._started = clock()
        self.stage_durations: dict[str, float] = {}

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        started = self._clock()
        try:
            yield
        finally:
            self.stage_durations[stage] = max(0.0, self._clock() - started)

    @property
    def total_duration(self) -> float:
        return max(0.0, self._clock() - self._started)
