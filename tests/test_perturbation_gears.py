from __future__ import annotations

import pytest

gears = pytest.importorskip("gears")

from cradle.contracts.errors import NotConfiguredError  # noqa: E402
from cradle.registry import discover  # noqa: E402
from perturbation_gears.adapter import MODEL_DIR, build_adapter  # noqa: E402


@pytest.fixture(scope="module")
def adapter():
    return build_adapter()


def _skip_if_not_trained():
    if not (MODEL_DIR / "model.pt").exists():
        pytest.skip(
            "gears has no trained model yet - run "
            "scripts/perturbation_gears/train_and_evaluate.py first"
        )


def test_adapter_is_discoverable():
    found = [p for p in discover("ai_model_adapter") if p.entry_point_name == "gears"]
    assert len(found) == 1
    assert found[0].instance.contract_type == "perturbation"


def test_predict_raises_not_configured_error_with_a_clear_message_when_untrained(
    adapter, monkeypatch
):
    """The gate itself is real and independent of whether training has
    actually finished in this environment - force the "not trained" path
    directly rather than relying on timing.
    """
    import perturbation_gears.adapter as adapter_module

    monkeypatch.setattr(adapter_module, "_gears_model", None)
    monkeypatch.setattr(adapter_module, "MODEL_DIR", adapter_module.MODEL_DIR / "definitely_missing")

    with pytest.raises(NotConfiguredError, match="train_and_evaluate.py"):
        adapter.predict({"genes_to_perturb": ["KLF1"]})


def test_predict_returns_a_real_valid_vector_delta_prediction(adapter):
    _skip_if_not_trained()

    result = adapter.predict({"genes_to_perturb": ["KLF1"]})
    assert set(result["output"]["gene_deltas"].keys())
    assert len(result["output"]["gene_deltas"]) <= 20
    assert all(isinstance(v, float) for v in result["output"]["gene_deltas"].values())
    assert result["provenance"]["is_trained_model"] is True
    assert result["provenance"]["kind"] == "vector_delta"
    assert "uncertainty_log_variance" in result["provenance"]


def test_predict_is_deterministic_for_the_same_perturbation(adapter):
    _skip_if_not_trained()

    first = adapter.predict({"genes_to_perturb": ["KLF1"]})["output"]["gene_deltas"]
    second = adapter.predict({"genes_to_perturb": ["KLF1"]})["output"]["gene_deltas"]
    assert first == second


def test_predict_actually_depends_on_which_gene_is_perturbed(adapter):
    """Not a shape-only check: two different real gene knockouts must
    produce different predicted responses, or the model isn't actually
    reading the requested perturbation.
    """
    _skip_if_not_trained()

    model = build_adapter()
    from perturbation_gears.adapter import _get_model

    real_model = _get_model()
    pert_list = [g for g in ("KLF1", "BAK1", "CEBPE", "SET") if g in real_model.pert_list]
    if len(pert_list) < 2:
        pytest.skip("fewer than 2 of the probe genes are in this trained model's perturbation graph")

    first = model.predict({"genes_to_perturb": [pert_list[0]]})["output"]["gene_deltas"]
    second = model.predict({"genes_to_perturb": [pert_list[1]]})["output"]["gene_deltas"]
    assert first != second


def test_predict_rejects_a_gene_not_in_the_perturbation_graph(adapter):
    _skip_if_not_trained()

    with pytest.raises(ValueError, match="perturbation graph"):
        adapter.predict({"genes_to_perturb": ["DEFINITELY_NOT_A_REAL_GENE_XYZ"]})
