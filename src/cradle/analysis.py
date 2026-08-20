from __future__ import annotations


def count_local_maxima(values: list[float]) -> int:
    """Count strict local maxima in a trajectory.

    Used to validate oscillatory (limit-cycle) models, where point-by-point
    trajectory agreement between two solvers is the wrong test — small
    numerical differences accumulate into phase drift over many periods
    even when both integrators are correct. Peak count and amplitude range
    (`amplitude_range`) are phase-invariant features appropriate to that
    class of model; exact final-value agreement (as used for the Phase 1
    toggle switch, a fixed-point system) is not.
    """
    return sum(
        1
        for i in range(1, len(values) - 1)
        if values[i] > values[i - 1] and values[i] > values[i + 1]
    )


def amplitude_range(values: list[float]) -> tuple[float, float]:
    return min(values), max(values)
