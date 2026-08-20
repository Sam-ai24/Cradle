from __future__ import annotations

from typing import Any

from depmap_data.connector import DepMapConnector

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.perturbation import SCALAR_PHENOTYPE, validate_perturbation_output


class EmpiricalGeneFitnessAdapter:
    """Perturbation contract, `scalar_phenotype` kind (Phase 8's
    gene-fitness-screen category).

    An **empirical baseline**: reports the real, measured mean CRISPR
    gene-effect score from DepMap Achilles across cell lines — not a
    prediction for a *new* cell line or condition. `usable_for_training`
    mirrors the connector's `training_eligible: False` flag: DepMap's
    license explicitly forbids using this data to train or enhance ML
    models, so any future training pipeline built on this adapter's
    output has something concrete to check, not just a comment to miss.
    """

    name = "gene-fitness-empirical"
    contract_type = "perturbation"
    usable_for_training = False
    conformance_input = {"gene_symbol": "KRAS"}  # a real, common-essential-in-many-lines gene

    def __init__(self) -> None:
        self._depmap = DepMapConnector()

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        gene_symbol = input["gene_symbol"]
        record = self._depmap.fetch(f"depmap.gene:{gene_symbol}")
        data = record["data"]

        output = {
            "phenotype_name": "crispr_gene_effect_mean_across_cell_lines",
            "phenotype_score": data["mean_gene_effect"],
            "phenotype_score_stdev": data["stdev_gene_effect"],
            "n_cell_lines": data["cell_line_count"],
        }
        validate_perturbation_output(SCALAR_PHENOTYPE, output)

        return {
            "output": output,
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "kind": SCALAR_PHENOTYPE,
                "method": "empirical_mean_lookup",
                "is_trained_model": False,
                "training_eligible": False,
                "source_curie": f"depmap.gene:{gene_symbol}",
            },
        }
