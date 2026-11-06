from __future__ import annotations

from src.diagnostics import InteractionTimer
from src.models import InteractionDiagnostics


def test_timer_records_only_executed_stages_and_total_duration() -> None:
    ticks = iter([0.0, 1.0, 2.5, 5.0])
    timer = InteractionTimer(clock=lambda: next(ticks))

    with timer.measure("classification"):
        pass

    diagnostics = InteractionDiagnostics(
        route="cache_hit",
        stage_durations=timer.stage_durations,
        total_duration=timer.total_duration,
    )

    assert diagnostics.stage_durations == {"classification": 1.5}
    assert "retrieval" not in diagnostics.stage_durations
    assert diagnostics.total_duration == 5.0
