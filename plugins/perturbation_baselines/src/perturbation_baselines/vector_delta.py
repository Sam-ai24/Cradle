from __future__ import annotations

from typing import Any

from scperturb_data.connector import ScPerturbConnector

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.perturbation import VECTOR_DELTA, validate_perturbation_output


class EmpiricalVectorDeltaAdapter:
    """Perturbation contract, `vector_delta` kind — the shape Phase 5's
    contract already used, now backed by a real empirical source
    (Phase 8's gene-edit and drug categories both fit this shape).

    An **empirical baseline**: the real, measured mean per-gene
    expression change (normalized, log1p) between a named perturbation
    group and its dataset's own control group in a harmonized scPerturb
    dataset — not a prediction for an unseen perturbation.
    """

    name = "perturbseq-vector-delta-empirical"
    contract_type = "perturbation"
    conformance_input = {
        "dataset_key": "DixitRegev2016_K562_TFs_13_days",
        "perturbation_label": "p-sgIRF1-2",
    }

    def __init__(self) -> None:
        self._scperturb = ScPerturbConnector()

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        dataset_key = input["dataset_key"]
        perturbation_label = input["perturbation_label"]

        record = self._scperturb.fetch(f"scperturb:{dataset_key}:{perturbation_label}")
        data = record["data"]

        output = {
            "gene_deltas": data["top_gene_deltas"],
            "perturbation_type": data["perturbation_type"],
            "n_perturbed_cells": data["n_perturbed_cells"],
            "n_control_cells": data["n_control_cells"],
            "target_gene": data["target_gene"],
            "target_gene_self_delta": data["target_gene_self_delta"],
        }
        validate_perturbation_output(VECTOR_DELTA, output)

        return {
            "output": output,
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "kind": VECTOR_DELTA,
                "method": "empirical_normalized_mean_difference",
                "is_trained_model": False,
                "source_curie": f"scperturb:{dataset_key}:{perturbation_label}",
            },
        }
