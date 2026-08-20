from __future__ import annotations

#: Extends the Phase 5 perturbation AI contract (Architecture, Layer 5)
#: from one generic shape into the several real intervention types
#: actually need — additive, not breaking: an adapter that only ever
#: returns "vector_delta" (Phase 5's original shape) still satisfies the
#: base AIModelAdapter contract unchanged. This module is the shared
#: vocabulary every perturbation adapter and every caller of one agrees
#: on for the newly distinguished output kinds.

VECTOR_DELTA = "vector_delta"
SCALAR_PHENOTYPE = "scalar_phenotype"
DOSE_CURVE = "dose_curve"
TRAJECTORY = "trajectory"

ALL_KINDS = (VECTOR_DELTA, SCALAR_PHENOTYPE, DOSE_CURVE, TRAJECTORY)

#: Required keys inside `output` for each kind, discovered by validating
#: against real fetched data per intervention category (Phase 8) rather
#: than designed in the abstract:
#:   - vector_delta: gene edits (Perturb-seq-style) fit this as-is —
#:     a per-gene expression change from a baseline.
#:   - scalar_phenotype: gene-fitness screens (DepMap-style) collapse to
#:     one number per perturbation, not a vector.
#:   - dose_curve: drug response is a function of concentration, not a
#:     single before/after point.
#:   - trajectory: aging is indexed by age/time, not a single delta.
_REQUIRED_FIELDS = {
    VECTOR_DELTA: {"gene_deltas"},
    SCALAR_PHENOTYPE: {"phenotype_name", "phenotype_score"},
    DOSE_CURVE: {"doses", "responses", "dose_units"},
    TRAJECTORY: {"index_values", "index_label", "values"},
}


class InvalidPerturbationOutputError(ValueError):
    pass


def validate_perturbation_output(kind: str, output: dict) -> None:
    """Check that `output` (the `output` field of a perturbation adapter's
    `ModelPrediction`) actually has the shape its declared `kind` promises.
    This is what makes the contract extension real rather than
    documentation: any adapter claiming a `kind` is mechanically checked
    against it, the same way `cradle.conformance` gates every other
    typed contract.
    """
    if kind not in _REQUIRED_FIELDS:
        raise InvalidPerturbationOutputError(
            f"unknown perturbation kind '{kind}'; expected one of {ALL_KINDS}"
        )
    missing = _REQUIRED_FIELDS[kind] - output.keys()
    if missing:
        raise InvalidPerturbationOutputError(
            f"perturbation output declared kind='{kind}' but is missing {sorted(missing)}"
        )
