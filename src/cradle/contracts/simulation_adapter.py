from __future__ import annotations

from typing import Any, Protocol, TypedDict, runtime_checkable


class SimulationResult(TypedDict):
    t: list[float]
    trajectories: dict[str, list[float]]
    engine: str


@runtime_checkable
class SimulationAdapter(Protocol):
    """Contract for a pluggable simulation engine (Architecture, Layer 4).

    Mirrors the shape of the BioSimulators `exec_sed_task()` convention: a
    model plus a run configuration go in, a standardized trajectory comes
    out, tagged with which engine produced it. Phase 2 replaces the plain
    dict `model`/`config` here with real SBML models and SED-ML/COMBINE
    archives; this adapter boundary itself doesn't change.
    """

    name: str

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult: ...
