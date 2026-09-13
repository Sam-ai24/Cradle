from __future__ import annotations

import pytest

from cradle.conformance.fixtures import build_reference_fba_sbml
from cradle.registry import discover
from cradle.substrate.examples.toy_fba import EXPECTED_OPTIMAL_SECRETION_FLUX

pytest.importorskip("cobra")


def _cobrapy_adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "cobrapy":
            return plugin.instance
    pytest.skip("'cobrapy' simulation adapter is not installed")


def test_cobrapy_adapter_solves_the_toy_network_correctly(tmp_path):
    """Not just a shape check: the toy uptake->conversion->secretion network
    has an analytically obvious optimum (secretion flux is bounded by, and
    must equal, the uptake bound) — verifying against it catches a wrong
    answer that a schema-only conformance check would miss.
    """
    sbml_path = build_reference_fba_sbml(str(tmp_path))
    adapter = _cobrapy_adapter()

    result = adapter.run({"sbml_path": sbml_path}, {})

    assert result["status"] == "optimal"
    assert result["objective_value"] == pytest.approx(EXPECTED_OPTIMAL_SECRETION_FLUX)
    assert result["trajectories"]["secretion"][0] == pytest.approx(
        EXPECTED_OPTIMAL_SECRETION_FLUX
    )
    assert result["trajectories"]["uptake"][0] == pytest.approx(
        EXPECTED_OPTIMAL_SECRETION_FLUX
    )


def test_cobrapy_gene_table_and_single_gene_deletion_on_the_toy_network(tmp_path):
    """The flagship path (`--gene-table` / `--single-gene-deletion`) has to
    keep working on the tiny network, not only on iML1515 — otherwise a
    JSON-shape bug in the new worker commands would only show up after a
    multi-minute genome-scale run.
    """
    sbml_path = build_reference_fba_sbml(str(tmp_path))
    adapter = _cobrapy_adapter()

    table = adapter.gene_table(sbml_path)
    # The Phase 2 toy network has no GPR/genes — that's a real property of
    # the fixture, not a worker bug. The new commands still have to return
    # a well-formed payload and the same optimum as `run()`.
    assert table["n_genes"] == len(table["genes"])
    gene_ids = {gene["id"] for gene in table["genes"]}

    deletions = adapter.single_gene_deletion(sbml_path)
    assert deletions["baseline_growth"] == pytest.approx(EXPECTED_OPTIMAL_SECRETION_FLUX)
    assert set(deletions["genes"]) == gene_ids
    for knockout in deletions["genes"].values():
        assert "growth" in knockout
        assert "status" in knockout
