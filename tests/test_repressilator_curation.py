from __future__ import annotations

from pathlib import Path

import pytest

from cradle.analysis import amplitude_range, count_local_maxima
from cradle.curation import read_curation_record
from cradle.registry import discover

pytest.importorskip("tellurium")
pytest.importorskip("basico")

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "repressilator"
ARCHIVE_PATH = str(MODEL_DIR / "repressilator.omex")
MIN_EXPECTED_PEAKS = 3


def _adapter(entry_point_name: str):
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == entry_point_name:
            return plugin.instance
    pytest.skip(f"'{entry_point_name}' simulation adapter is not installed")


def test_curation_record_reflects_a_real_promotion():
    record = read_curation_record(MODEL_DIR / "curation.json")
    assert record["tier"] == "curated"
    assert record["model_curie"] == "biomodels.db:BIOMD0000000012"
    assert set(record["adapters_used"]) == {"tellurium", "copasi"}
    assert len(record["evidence"]) >= 4


@pytest.mark.parametrize("adapter_name", ["tellurium", "copasi"])
def test_published_archive_reproduces_sustained_oscillation(adapter_name: str):
    """Phase 4 exit criterion: take the *published* archive — not a freshly
    rebuilt one — and reproduce the original result on a registered
    adapter with no additional input beyond the archive file itself.
    Parametrized over both adapters this model was curated with, so
    reproducing on "a different registered adapter" than any one choice
    of primary engine is demonstrated either way.
    """
    assert Path(ARCHIVE_PATH).exists(), "run scripts/curate_repressilator.py first"

    adapter = _adapter(adapter_name)
    result = adapter.run({"combine_archive": ARCHIVE_PATH}, {})

    px = result["trajectories"]["PX"]
    peaks = count_local_maxima(px)
    low, high = amplitude_range(px)

    assert peaks >= MIN_EXPECTED_PEAKS, (
        f"{adapter_name} reproduced only {peaks} peaks from the published archive, "
        f"expected sustained oscillation (>= {MIN_EXPECTED_PEAKS})"
    )
    assert high > 10 * max(low, 1e-9), f"{adapter_name} shows no real oscillation amplitude"
