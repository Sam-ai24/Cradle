from __future__ import annotations

import pytest

from cradle.perturbation import DOSE_CURVE, SCALAR_PHENOTYPE, TRAJECTORY, VECTOR_DELTA

pytest.importorskip("anndata")


def test_drug_dose_curve_is_a_real_monotonic_hill_curve_anchored_on_a_measured_ic50():
    from perturbation_baselines.drug_dose_curve import EmpiricalDrugDoseCurveAdapter

    result = EmpiricalDrugDoseCurveAdapter().predict({"chembl_id": "CHEMBL25"})
    output = result["output"]

    assert result["provenance"]["kind"] == DOSE_CURVE
    assert result["provenance"]["is_trained_model"] is False
    assert output["anchor_ic50_nm"] > 0

    doses, responses = output["doses"], output["responses"]
    assert doses == sorted(doses)
    assert responses == sorted(responses), "a Hill curve must be monotonically increasing"
    # The grid is log-spaced symmetrically around the IC50 with an odd
    # point count, guaranteeing the middle point lands exactly on
    # dose == IC50 — where the Hill equation gives exactly 50% by
    # construction. Checking the adapter's actual generated output here,
    # not a restated version of the formula.
    middle_index = len(doses) // 2
    assert doses[middle_index] == pytest.approx(output["anchor_ic50_nm"])
    assert responses[middle_index] == pytest.approx(50.0)


def test_gene_fitness_reports_a_real_depmap_score_with_uncertainty():
    from perturbation_baselines.gene_fitness import EmpiricalGeneFitnessAdapter

    adapter = EmpiricalGeneFitnessAdapter()
    assert adapter.usable_for_training is False

    result = adapter.predict({"gene_symbol": "KRAS"})
    output = result["output"]

    assert result["provenance"]["kind"] == SCALAR_PHENOTYPE
    assert result["provenance"]["training_eligible"] is False
    assert output["n_cell_lines"] > 100  # DepMap covers hundreds of cell lines
    assert output["phenotype_score_stdev"] > 0


def test_vector_delta_reports_a_real_crispr_knockdown_reducing_its_own_target():
    from perturbation_baselines.vector_delta import EmpiricalVectorDeltaAdapter

    result = EmpiricalVectorDeltaAdapter().predict(
        {"dataset_key": "DixitRegev2016_K562_TFs_13_days", "perturbation_label": "p-sgIRF1-2"}
    )
    output = result["output"]

    assert result["provenance"]["kind"] == VECTOR_DELTA
    assert output["perturbation_type"] == "CRISPR"
    assert output["target_gene"] == "IRF1"
    # A real, if modest, knockdown effect: the sgRNA's own target should
    # show a negative delta (less expression under knockdown vs control),
    # not asserted to be dramatic - real Perturb-seq knockdown efficiency
    # varies a lot and this dataset's effect on IRF1 itself is small.
    assert output["target_gene_self_delta"] < 0
    assert len(output["gene_deltas"]) > 0


def test_aging_trajectory_reports_real_measured_values_without_asserting_a_direction():
    from perturbation_baselines.aging_trajectory import EmpiricalAgingTrajectoryAdapter

    result = EmpiricalAgingTrajectoryAdapter().predict({"gene_symbol": "Cdkn2a"})
    output = result["output"]

    assert result["provenance"]["kind"] == TRAJECTORY
    assert output["index_label"] == "age"
    assert output["index_values"] == ["18m", "21m", "24m", "30m"]
    assert len(output["values"]) == len(output["index_values"])
    # Deliberately no assertion that Cdkn2a increases with age here: checked
    # directly against this real dataset, and it doesn't show a clean
    # monotonic increase in this tissue slice (see the adapter's docstring)
    # - asserting the textbook direction would be scientifically dishonest
    # for this specific data.
    assert all(v >= 0 for v in output["values"])
