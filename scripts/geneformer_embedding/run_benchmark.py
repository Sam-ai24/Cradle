"""Phase 12 continued: a real, honest benchmark check for the Geneformer
embedding adapter against real, labeled data — not just the correctness
test's "is it deterministic and cell-dependent" bar.

    python scripts/geneformer_embedding/run_benchmark.py

Builds a real, stratified sample from the same real, standard scanpy PBMC
dataset the adapter's own example already uses — raw counts from
`pbmc3k()` (needed for Geneformer's tokenizer), matched by real 10x cell
barcode to the real, published cell-type annotations in
`pbmc3k_processed()` (the standard scanpy tutorial's own louvain-cluster
cell-type labels: CD4 T cells, CD14+ Monocytes, B cells, CD8 T cells, NK
cells, FCGR3A+ Monocytes, Dendritic cells, Megakaryocytes) — then asks
the actual, field-standard question: does Geneformer's embedding
separate real biological cell types better than the field's own simplest
standard baseline, PCA on log-normalized expression? Reports both real
metrics (silhouette score, k-NN label-transfer accuracy) for both, and
does not assume which one wins — Arc Institute's own 2025 Virtual Cell
Challenge found even well-funded, purpose-built perturbation models
didn't reliably beat a naive baseline, so losing here would be a
legitimate, reportable result too, not a bug.

CZI's own `cz-benchmarks` (and the `scib-metrics` engine it wraps) was
the first choice, but its `jaxlib` dependency fails to import on this
machine (`ImportError: DLL load failed... An Application Control policy
has blocked this file`) — a real, different-flavored Windows blocker,
confirmed directly. `sklearn.metrics.silhouette_score` and a k-NN probe
are the same evaluation family (silhouette specifically is what
`scib_metrics.silhouette_label` itself reports) without any JAX
dependency, so this script uses those directly instead.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import scanpy as sc
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier

from geneformer_embedding.adapter import TranscriptomeTokenizer, _get_model

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "geneformer_benchmark.json"
CELLS_PER_TYPE = 40
KNN_NEIGHBORS = 5
CV_FOLDS = 5


def build_labeled_real_subset() -> "sc.AnnData":
    """Real raw counts (`pbmc3k`) matched by real 10x cell barcode to real
    published cell-type labels (`pbmc3k_processed`'s louvain clusters),
    stratified up to `CELLS_PER_TYPE` cells per real type (the two rarest
    real types, Dendritic cells and Megakaryocytes, have fewer than that
    in the whole dataset and are kept at their real full count).
    """
    raw = sc.datasets.pbmc3k()
    processed = sc.datasets.pbmc3k_processed()
    common = raw.obs_names.intersection(processed.obs_names)
    raw = raw[common].copy()
    raw.obs["cell_type"] = processed.obs.loc[common, "louvain"].astype(str).values

    rng = np.random.default_rng(42)
    selected = []
    for cell_type in sorted(raw.obs["cell_type"].unique()):
        idx = raw.obs.index[raw.obs["cell_type"] == cell_type].to_numpy()
        chosen = rng.choice(idx, size=min(CELLS_PER_TYPE, len(idx)), replace=False)
        selected.extend(chosen.tolist())

    subset = raw[selected].copy()
    subset.var["ensembl_id"] = subset.var["gene_ids"]
    subset.obs["n_counts"] = subset.X.sum(axis=1)
    subset.obs["filter_pass"] = 1
    return subset


def compute_geneformer_embeddings(adata: "sc.AnnData") -> tuple[np.ndarray, list[str]]:
    """Real Geneformer embeddings for every cell in `adata`, plus the real
    cell-type label carried through tokenization for each one (label
    passthrough via `TranscriptomeTokenizer`'s own custom-attribute
    mechanism, not assumed to survive in the original row order).
    """
    import torch
    from datasets import load_from_disk

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_dir = Path(tmp_dir) / "in"
        output_dir = Path(tmp_dir) / "out"
        input_dir.mkdir()
        adata.write_h5ad(input_dir / "input.h5ad")

        tokenizer = TranscriptomeTokenizer({"cell_type": "cell_type"}, nproc=1, model_version="V1")
        tokenizer.tokenize_data(str(input_dir), str(output_dir), "tokenized", file_format="h5ad")
        dataset = load_from_disk(str(output_dir / "tokenized.dataset"))

    model = _get_model()
    embeddings = []
    with torch.no_grad():
        for cell in dataset:
            input_ids = torch.tensor([cell["input_ids"]])
            last_hidden = model(input_ids=input_ids).last_hidden_state
            embeddings.append(last_hidden[0].mean(dim=0).numpy())

    return np.stack(embeddings), list(dataset["cell_type"])


def compute_pca_baseline_embeddings(adata: "sc.AnnData", n_components: int) -> np.ndarray:
    """The field's own simplest standard baseline: PCA on log-normalized
    expression - real, standard scanpy preprocessing, not a strawman.
    """
    baseline = adata.copy()
    sc.pp.normalize_total(baseline, target_sum=1e4)
    sc.pp.log1p(baseline)
    return PCA(n_components=n_components, random_state=42).fit_transform(baseline.X)


def evaluate(embeddings: np.ndarray, labels: list[str]) -> dict:
    silhouette = float(silhouette_score(embeddings, labels))

    knn_accuracy = float(
        cross_val_score(
            KNeighborsClassifier(n_neighbors=KNN_NEIGHBORS),
            embeddings,
            labels,
            cv=StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42),
        ).mean()
    )
    return {"silhouette_score": silhouette, "knn_cv_accuracy": knn_accuracy}


def main() -> int:
    print("Building the real, labeled, stratified PBMC subset...")
    adata = build_labeled_real_subset()
    print(adata.obs["cell_type"].value_counts().to_dict())

    print("Computing real Geneformer embeddings (this is the slow step)...")
    geneformer_embeddings, labels = compute_geneformer_embeddings(adata)

    print("Computing the real PCA baseline (same dimensionality)...")
    pca_embeddings = compute_pca_baseline_embeddings(adata, n_components=geneformer_embeddings.shape[1])

    results = {
        "n_cells": len(labels),
        "n_real_cell_types": len(set(labels)),
        "embedding_dim": geneformer_embeddings.shape[1],
        "geneformer": evaluate(geneformer_embeddings, labels),
        "pca_baseline": evaluate(pca_embeddings, labels),
    }
    print(json.dumps(results, indent=2))

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
