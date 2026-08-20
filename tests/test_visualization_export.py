from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

pytest.importorskip("tellurium")
pytest.importorskip("basico")

import export_visualization_data as export_module  # noqa: E402


def test_export_graph_reflects_the_models_own_real_annotations():
    """Not hardcoded: the graph must come from the model's own MIRIAM
    CVTerms (Phase 1/4), so if the published model ever changes, this
    export changes with it rather than silently going stale.
    """
    graph, accession_by_species = export_module.export_graph()

    node_ids = {n["data"]["id"] for n in graph["elements"]["nodes"]}
    assert node_ids == {"PX", "PY", "PZ"}

    curies_by_id = {n["data"]["id"]: n["data"]["curie"] for n in graph["elements"]["nodes"]}
    assert curies_by_id["PX"] == "uniprot:P03023"  # LacI
    assert curies_by_id["PY"] == "uniprot:P04483"  # TetR
    assert curies_by_id["PZ"] == "uniprot:P03034"  # lambda CI

    assert accession_by_species == {"PX": "P03023", "PY": "P04483", "PZ": "P03034"}

    edges = {(e["data"]["source"], e["data"]["target"]) for e in graph["elements"]["edges"]}
    assert edges == {("PX", "PY"), ("PY", "PZ"), ("PZ", "PX")}


def test_export_trajectories_returns_both_registered_adapters(tmp_path, monkeypatch):
    trajectories = export_module.export_trajectories()

    assert set(trajectories) == {"tellurium", "copasi"}
    for engine, data in trajectories.items():
        assert len(data["t"]) == len(data["PX"]) > 0
        assert all(v >= 0 for v in data["PX"]), f"{engine} produced a negative concentration"
