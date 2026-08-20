from __future__ import annotations

from typing import Any

from chembl_data.connector import ChEMBLConnector

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.perturbation import DOSE_CURVE, validate_perturbation_output


class EmpiricalDrugDoseCurveAdapter:
    """Perturbation contract, `dose_curve` kind (Phase 8's drug category).

    This is an **empirical baseline**, not a trained predictive model: it
    fetches a real measured IC50 from ChEMBL for the requested compound
    (optionally filtered by target name) and generates the theoretical
    sigmoidal Hill-equation curve that IC50 parameterizes —
    `inhibition(dose) = 100 * dose^n / (dose^n + IC50^n)` — the same
    standard pharmacology construction used to visualize a measured IC50
    as a curve. The anchor value is real; the curve shape between
    measured points is the textbook equation, not additional
    measurements. VCBench and similar benchmarks compare AI models
    against exactly this kind of "naive/empirical baseline" — this is
    Cradle's, not a stand-in for a real predictive model.
    """

    name = "drug-dose-curve-empirical"
    contract_type = "perturbation"
    conformance_input = {"chembl_id": "CHEMBL25"}  # aspirin, has real IC50 records

    def __init__(self) -> None:
        self._chembl = ChEMBLConnector()

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        chembl_id = input["chembl_id"]
        target_filter = input.get("target_name_contains")
        hill_coefficient = input.get("hill_coefficient", 1.0)
        # Odd by construction (default 11, and any caller-supplied value is
        # nudged up to the next odd number): a symmetric log-spaced grid
        # with an odd point count always lands exactly on the midpoint
        # (dose == IC50), which is what makes that point mathematically
        # checkable against the Hill equation's known 50% value there.
        n_points = input.get("n_points", 11)
        if n_points % 2 == 0:
            n_points += 1

        record = self._chembl.fetch(f"chembl:{chembl_id}")
        ic50_records = record["data"]["ic50_records"]
        if target_filter:
            ic50_records = [
                r for r in ic50_records if target_filter.lower() in (r["target"] or "").lower()
            ]
        if not ic50_records:
            raise ValueError(f"no IC50 record found for '{chembl_id}' (target filter={target_filter!r})")

        ic50_nm = ic50_records[0]["ic50_nm"]
        doses = [ic50_nm * (10 ** exponent) for exponent in _log_range(-2, 2, n_points)]
        responses = [
            100.0 * (dose**hill_coefficient) / (dose**hill_coefficient + ic50_nm**hill_coefficient)
            for dose in doses
        ]

        output = {
            "doses": doses,
            "responses": responses,
            "dose_units": "nM",
            "response_units": "percent_inhibition",
            "anchor_ic50_nm": ic50_nm,
            "anchor_target": ic50_records[0]["target"],
        }
        validate_perturbation_output(DOSE_CURVE, output)

        return {
            "output": output,
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "kind": DOSE_CURVE,
                "method": "hill_equation_parameterized_by_measured_ic50",
                "is_trained_model": False,
                "source_curie": f"chembl:{chembl_id}",
            },
        }


def _log_range(start_exponent: float, stop_exponent: float, n_points: int) -> list[float]:
    step = (stop_exponent - start_exponent) / (n_points - 1)
    return [start_exponent + i * step for i in range(n_points)]
