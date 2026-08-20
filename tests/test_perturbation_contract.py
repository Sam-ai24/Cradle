from __future__ import annotations

import pytest

from cradle.perturbation import (
    DOSE_CURVE,
    SCALAR_PHENOTYPE,
    TRAJECTORY,
    VECTOR_DELTA,
    InvalidPerturbationOutputError,
    validate_perturbation_output,
)


def test_accepts_a_well_formed_output_of_each_kind():
    validate_perturbation_output(VECTOR_DELTA, {"gene_deltas": {"A": 1.0}})
    validate_perturbation_output(
        SCALAR_PHENOTYPE, {"phenotype_name": "x", "phenotype_score": 1.0}
    )
    validate_perturbation_output(
        DOSE_CURVE, {"doses": [1.0], "responses": [1.0], "dose_units": "nM"}
    )
    validate_perturbation_output(
        TRAJECTORY, {"index_values": ["t0"], "index_label": "age", "values": [1.0]}
    )


def test_rejects_an_unknown_kind():
    with pytest.raises(InvalidPerturbationOutputError):
        validate_perturbation_output("not_a_real_kind", {})


def test_rejects_output_missing_required_fields_for_its_declared_kind():
    with pytest.raises(InvalidPerturbationOutputError):
        # dose_curve without doses/responses - the whole point of the kind
        validate_perturbation_output(DOSE_CURVE, {"dose_units": "nM"})


def test_existing_phase5_vector_delta_shape_is_unaffected_by_the_extension():
    """The additive-not-breaking claim, checked: a Phase 5-style adapter
    that only ever emits the original vector_delta shape still validates
    with zero changes needed on its part.
    """
    validate_perturbation_output(VECTOR_DELTA, {"gene_deltas": {"TP53": -0.4, "MDM2": 0.2}})
