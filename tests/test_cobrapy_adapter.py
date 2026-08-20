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
