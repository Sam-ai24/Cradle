"""Phase 12 continued: Cradle's first real *trained* model behind the
perturbation AI contract — GEARS (Roman-Rodriguez et al., Nature
Biotechnology 2023, MIT license), predicting a cell's transcriptional
response to a single or combinatorial gene knockout via a GNN over a
real Gene Ontology similarity network.

Requires a model already trained by
`scripts/perturbation_gears/train_and_evaluate.py` (real training on the
real Norman et al. 2019 Perturb-seq dataset — not something `predict()`
can do on the fly). If that hasn't been run yet, `predict()` raises
`NotConfiguredError` with instructions, the same skip-not-fail signal
Phase 3/5's key/license gates use — this is a genuinely different reason
(no trained checkpoint yet, not a missing credential), but the same
shape: an optional capability that isn't ready in a fresh environment,
reported as a skip rather than a crash.

The `PertData` split parameters here (`split="simulation", seed=1`) MUST
match `train_and_evaluate.py`'s exactly — they determine the real gene
similarity network topology the trained weights were fit against, not
just a convenience default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cradle.contracts.ai_model_adapter import ModelPrediction
from cradle.contracts.errors import NotConfiguredError
from cradle.perturbation import VECTOR_DELTA, validate_perturbation_output

from perturbation_gears.compat_patches import patch_gears
from perturbation_gears.device import resolve_device

DATA_CACHE_DIR = Path.home() / ".cradle" / "cache" / "gears_norman"
MODEL_DIR = Path.home() / ".cradle" / "cache" / "gears_norman_model"
SPLIT_KWARGS = {"split": "simulation", "seed": 1}
TOP_N_GENES = 20

_gears_model = None  # lazy singleton, same pattern as esmc_embedding/geneformer_embedding


def _get_model():
    global _gears_model
    if _gears_model is not None:
        return _gears_model

    if not (MODEL_DIR / "model.pt").exists():
        raise NotConfiguredError(
            "'gears' has no trained model yet — run "
            "'python scripts/perturbation_gears/train_and_evaluate.py' first "
            "(downloads the real Norman et al. 2019 dataset and trains for real; "
            "see that script's module docstring for expected runtime). Every other "
            "part of Cradle works without this."
        )

    patch_gears()
    from gears import GEARS, PertData

    pert_data = PertData(str(DATA_CACHE_DIR))
    pert_data.load(data_name="norman")
    pert_data.prepare_split(**SPLIT_KWARGS)
    pert_data.get_dataloader(batch_size=32, test_batch_size=128)

    model = GEARS(pert_data, device=resolve_device())
    model.load_pretrained(str(MODEL_DIR))
    _gears_model = model
    return _gears_model


class GearsPerturbationAdapter:
    """Perturbation contract, `vector_delta` kind (Architecture, Layer 5) —
    the real, trained counterpart to
    `perturbation_baselines.vector_delta.EmpiricalVectorDeltaAdapter`'s
    empirical lookup: this predicts the response to a perturbation GEARS
    was never directly trained on (within the limits of its "simulation"
    held-out split), rather than reporting an already-measured one.
    """

    name = "gears-norman"
    contract_type = "perturbation"
    conformance_input = {"genes_to_perturb": ["KLF1"]}

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        genes_to_perturb: list[str] = input["genes_to_perturb"]
        if len(genes_to_perturb) not in (1, 2):
            raise ValueError("GEARS predicts single or combinatorial (2-gene) perturbations only")

        model = _get_model()
        pert_spec = genes_to_perturb if len(genes_to_perturb) == 2 else [genes_to_perturb[0], "ctrl"]
        for gene in genes_to_perturb:
            if gene not in model.pert_list:
                raise ValueError(
                    f"'{gene}' is not in GEARS' perturbation graph for this trained model "
                    f"(it has no real Gene Ontology similarity data) — see GEARS.pert_list"
                )

        predictions, log_variances = model.predict([pert_spec])
        key = "_".join(pert_spec)
        predicted_expression = predictions[key]
        log_variance = log_variances[key]

        ctrl_mean = model.ctrl_expression.detach().cpu().numpy()
        deltas = predicted_expression - ctrl_mean

        top_indices = abs(deltas).argsort()[::-1][:TOP_N_GENES]
        gene_deltas = {model.gene_list[i]: float(deltas[i]) for i in top_indices}

        output = {"gene_deltas": gene_deltas}
        validate_perturbation_output(VECTOR_DELTA, output)

        return {
            "output": output,
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "kind": VECTOR_DELTA,
                "method": "gears_gnn_prediction",
                "is_trained_model": True,
                "genes_perturbed": genes_to_perturb,
                "uncertainty_log_variance": float(log_variance),
                "reference_dataset": "norman_2019_perturbseq",
            },
        }


def build_adapter() -> GearsPerturbationAdapter:
    return GearsPerturbationAdapter()
