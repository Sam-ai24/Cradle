from __future__ import annotations

import pytest

from cradle.conformance.fixtures import (
    REFERENCE_NUMBER_OF_STEPS,
    REFERENCE_SPECIES_IDS,
    build_reference_combine_archive,
)
from cradle.registry import discover

pytest.importorskip("tellurium")
pytest.importorskip("basico")


def _adapter(kind: str, entry_point_name: str):
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == entry_point_name:
            return plugin.instance
    pytest.skip(f"'{entry_point_name}' simulation adapter is not installed")


def test_tellurium_and_copasi_agree_on_the_same_combine_archive(tmp_path):
    """Phase 2 exit criterion: the same COMBINE archive runs unmodified on
    two different registered adapters and produces numerically consistent
    results — the concrete proof that the Layer 4 swap boundary works, not
    just that it's designed to.
    """
    archive_path = build_reference_combine_archive(str(tmp_path))

    tellurium_adapter = _adapter("simulation_adapter", "tellurium")
    copasi_adapter = _adapter("simulation_adapter", "copasi")

    tellurium_result = tellurium_adapter.run({"combine_archive": archive_path}, {})
    copasi_result = copasi_adapter.run({"combine_archive": archive_path}, {})

    assert len(tellurium_result["t"]) == REFERENCE_NUMBER_OF_STEPS + 1
    assert len(copasi_result["t"]) == REFERENCE_NUMBER_OF_STEPS + 1

    for species_id in REFERENCE_SPECIES_IDS:
        t_final = tellurium_result["trajectories"][species_id][-1]
        c_final = copasi_result["trajectories"][species_id][-1]
        assert t_final == pytest.approx(c_final, rel=1e-3), (
            f"'{species_id}' final value disagrees across engines: "
            f"tellurium={t_final}, copasi={c_final}"
        )
