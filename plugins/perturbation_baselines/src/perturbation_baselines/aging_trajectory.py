from __future__ import annotations

from typing import Any

from aging_expression_data.connector import AgingExpressionConnector

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.perturbation import TRAJECTORY, validate_perturbation_output


class EmpiricalAgingTrajectoryAdapter:
    """Perturbation contract, `trajectory` kind (Phase 8's aging category).

    An **empirical baseline**: the real, measured mean expression of one
    gene across real donor ages in Tabula Muris Senis — not a fitted or
    extrapolated aging curve. Deliberately makes no claim about the
    trend's direction; checked directly against a real senescence marker
    (Cdkn2a) in this dataset, and it does not show a clean monotonic
    increase in this particular tissue slice. Real aging data reported as
    measured, not smoothed toward a textbook expectation.
    """

    name = "aging-trajectory-empirical"
    contract_type = "perturbation"
    conformance_input = {"gene_symbol": "Cdkn2a"}

    def __init__(self) -> None:
        self._aging = AgingExpressionConnector()

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        gene_symbol = input["gene_symbol"]
        record = self._aging.fetch(f"aging.gene:{gene_symbol}")
        data = record["data"]

        output = {
            "index_label": "age",
            "index_values": data["ages"],
            "values": [data["mean_expression_by_age"][age] for age in data["ages"]],
            "cell_counts": [data["cell_count_by_age"][age] for age in data["ages"]],
        }
        validate_perturbation_output(TRAJECTORY, output)

        return {
            "output": output,
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "kind": TRAJECTORY,
                "method": "empirical_mean_lookup_by_age_group",
                "is_trained_model": False,
                "source_curie": f"aging.gene:{gene_symbol}",
            },
        }
