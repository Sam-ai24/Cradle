from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

pytest.importorskip("tellurium")
pytest.importorskip("basico")

import export_visualization_data as export_module  # noqa: E402


def test_export_visualization_data_no_longer_exports_trajectories():
    """export_trajectories() was removed: index.html's comparison panel now
    calls the live Explorer API (see tests/test_explorer_server.py) for
    whatever combine_archive engines are currently registered, instead of
    reading a pre-baked pair of runs from a static file. Guards against
    silently reintroducing the frozen-snapshot behavior.
    """
    assert not hasattr(export_module, "export_trajectories")


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
