from __future__ import annotations

import pytest

from cradle.registry import discover
from cradle.substrate.examples.boolean_toggle import write_sbml


def _adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "boolean-qual":
            return plugin.instance
    pytest.skip("'boolean-qual' simulation adapter is not installed")


def test_mutual_repression_oscillates_from_the_symmetric_start(tmp_path):
    """A real dynamical-systems claim, not a shape check: under
    synchronous update, A(t+1)=NOT B(t), B(t+1)=NOT A(t) started from
    (1,1) must period-2 oscillate between (1,1) and (0,0) — provable by
    hand, not asserted without proof.
    """
    sbml_path = write_sbml(str(tmp_path / "toggle.xml"), initial_a=1, initial_b=1)
    result = _adapter().run({"sbml_path": sbml_path}, {"n_steps": 5})

    a = result["trajectories"]["A"]
    b = result["trajectories"]["B"]
    assert a == [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    assert b == [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]


def test_mutual_repression_reaches_a_fixed_point_from_an_asymmetric_start(tmp_path):
    """The same network started from (1,0) is already at a fixed point —
    a different, equally provable dynamical fact about the same rules,
    which a network that just always oscillated would get wrong.
    """
    sbml_path = write_sbml(str(tmp_path / "toggle.xml"), initial_a=1, initial_b=0)
    result = _adapter().run({"sbml_path": sbml_path}, {"n_steps": 4})

    assert result["trajectories"]["A"] == [1.0, 1.0, 1.0, 1.0, 1.0]
    assert result["trajectories"]["B"] == [0.0, 0.0, 0.0, 0.0, 0.0]
