"""Phase 12 continued: train and evaluate a real GEARS perturbation-
prediction model — Cradle's first real trained model behind the
perturbation AI contract (Architecture Layer 5), as opposed to the
empirical, non-ML baselines `plugins/perturbation_baselines/` already
provides for Phase 8's four intervention types.

    python scripts/perturbation_gears/train_and_evaluate.py [--epochs N]

GEARS (Roman-Rodriguez et al., Nature Biotechnology 2023, MIT license) is
a graph-neural-network model specifically designed for this exact task:
predict a cell's transcriptional response to a genetic perturbation
(single or combinatorial gene knockout), using a gene-similarity network
built from real Gene Ontology annotations. Trained here on the real
Norman et al. 2019 combinatorial CRISPR Perturb-seq dataset (89,357 real
cells, 236 real single/double perturbations), fetched via GEARS' own
`PertData` from a direct Harvard Dataverse URL — the same real reference
dataset GEARS' own paper benchmarks against.

Real, disclosed cost: on a CPU-only Windows machine, one epoch over the
full 89k-cell dataset took ~50-60 real minutes; a run was killed by
something outside this process' control partway through epoch 3 of a
5-epoch attempt (confirmed genuinely still training when it was stopped —
loss was decreasing normally, not stuck). This script now checkpoints
after every epoch specifically so that isn't fatal: interrupt it any
time and the most recent completed epoch's weights are still on disk and
loadable. `--epochs` defaults to 5 but is meant to be raised on faster
hardware (a real GPU or Apple Silicon `mps`, both auto-detected via
`perturbation_gears.device.resolve_device`) — more epochs should keep
helping, per the real per-epoch validation-loss trend already observed
(epoch 1 val MSE 0.0051 -> epoch 2 val MSE 0.0038).

Evaluated the same way the field (and Arc Institute's own Virtual Cell
Challenge) evaluates this task: Pearson correlation between predicted and
real held-out post-perturbation expression, on the top differentially-
expressed genes per perturbation - compared directly against the field's
own standard naive baseline (predict no change from the real control-cell
mean expression), using GEARS' own `compute_metrics` for both so the
comparison is apples-to-apples.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from perturbation_gears.compat_patches import patch_gears
from perturbation_gears.device import resolve_device

patch_gears()

from gears import GEARS, PertData  # noqa: E402
from gears.inference import compute_metrics, evaluate  # noqa: E402

DATA_CACHE_DIR = Path.home() / ".cradle" / "cache" / "gears_norman"
MODEL_DIR = Path.home() / ".cradle" / "cache" / "gears_norman_model"
RESULTS_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "gears_perturbation_benchmark.json"


def evaluate_naive_baseline(loader, ctrl_mean: torch.Tensor) -> dict:
    """The field's own standard naive baseline for this task: predict no
    change from the real control-cell mean expression, for every test
    cell. Mirrors `gears.inference.evaluate`'s own extraction of
    `pert_cat`/`truth`/`truth_de`/`pred_de` exactly, substituting the
    real control mean for the model's prediction, so `compute_metrics`
    can score both on identical footing.
    """
    pert_cat, pred, truth, pred_de, truth_de = [], [], [], [], []
    for batch in loader:
        batch_size = batch.y.shape[0]
        p = ctrl_mean.unsqueeze(0).expand(batch_size, -1)
        pert_cat.extend(batch.pert)
        pred.extend(p)
        truth.extend(batch.y)
        for i, de_idx in enumerate(batch.de_idx):
            pred_de.append(p[i, de_idx])
            truth_de.append(batch.y[i, de_idx])

    return {
        "pert_cat": np.array(pert_cat),
        "pred": torch.stack(pred).detach().cpu().numpy(),
        "truth": torch.stack(truth).detach().cpu().numpy(),
        "pred_de": torch.stack(pred_de).detach().cpu().numpy(),
        "truth_de": torch.stack(truth_de).detach().cpu().numpy(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    device = resolve_device()
    print(f"Using device: {device}", flush=True)

    print("Loading the real Norman et al. 2019 Perturb-seq dataset...", flush=True)
    pert_data = PertData(str(DATA_CACHE_DIR))
    pert_data.load(data_name="norman")
    pert_data.prepare_split(split="simulation", seed=1)
    pert_data.get_dataloader(batch_size=args.batch_size, test_batch_size=128)

    model = GEARS(pert_data, device=device)
    model.model_initialize(hidden_size=64, uncertainty=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        print(f"--- Epoch {epoch}/{args.epochs} ---", flush=True)
        model.train(epochs=1)
        model.save_model(str(MODEL_DIR))
        print(
            f"Checkpointed after epoch {epoch} to {MODEL_DIR} "
            f"({time.time() - t0:.1f}s elapsed so far)",
            flush=True,
        )
    train_seconds = time.time() - t0
    print(f"Training took {train_seconds:.1f}s total for {args.epochs} epochs", flush=True)

    test_loader = pert_data.dataloader["test_loader"]
    test_results = evaluate(test_loader, model.best_model, uncertainty=True, device=device)
    gears_metrics, _ = compute_metrics(test_results)

    ctrl_adata = pert_data.adata[pert_data.adata.obs["condition"] == "ctrl"]
    ctrl_mean = torch.tensor(np.asarray(ctrl_adata.X.mean(axis=0)).flatten(), dtype=torch.float32)
    baseline_results = evaluate_naive_baseline(test_loader, ctrl_mean)
    baseline_metrics, _ = compute_metrics(baseline_results)

    report = {
        "dataset": "norman_2019_perturbseq",
        "device": device,
        "n_train_epochs": args.epochs,
        "train_seconds": train_seconds,
        "n_test_perturbations": len(set(test_results["pert_cat"])),
        "gears": {"pearson_de": float(gears_metrics["pearson_de"]), "mse_de": float(gears_metrics["mse_de"])},
        "naive_baseline_predict_no_change": {
            "pearson_de": float(baseline_metrics["pearson_de"]),
            "mse_de": float(baseline_metrics["mse_de"]),
        },
    }
    print(json.dumps(report, indent=2), flush=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {RESULTS_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
