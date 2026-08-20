from __future__ import annotations

import anndata as ad
import numpy as np
import scipy.sparse as sp

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.cache import cached_download
from cradle.substrate.annotate import parse_curie

_ZENODO_RECORD = "https://zenodo.org/api/records/13350497/files/{filename}/content"

#: scPerturb harmonizes many independent Perturb-seq studies into one
#: Zenodo record; this is a small registry of the specific files this
#: connector knows how to read, not the full catalog (each file is
#: 45MB-2.5GB — see docs/RESOURCES.md; only datasets small enough to
#: reasonably cache locally are registered).
_KNOWN_DATASETS = {
    "AissaBenevolenskaya2021": "AissaBenevolenskaya2021.h5ad",  # real drug perturbation (osimertinib, crizotinib)
    "DixitRegev2016_K562_TFs_13_days": "DixitRegev2016_K562_TFs_13_days.h5ad",  # real CRISPR TF knockdown
}

_TOP_N_GENES = 20


class UnknownScPerturbDatasetError(KeyError):
    pass


class ScPerturbConnector:
    """Real single-cell perturbation (Perturb-seq) data (Architecture,
    Layer 7's intervention-validation extension; Phase 8's gene-edit and
    drug vector-delta categories), harmonized by the scPerturb project
    and hosted on Zenodo.

    CURIE shape: `scperturb:<dataset_key>:<perturbation_label>`, e.g.
    `scperturb:DixitRegev2016_K562_TFs_13_days:p-sgIRF1-2`. Downloads
    (and locally caches — these files are 45MB+, see
    `cradle.knowledge.cache`) the real h5ad, computes total-count-
    normalized, log1p mean expression for the named perturbation group
    vs. the dataset's own `control` group, and returns the top genes by
    |delta| — the `vector_delta` perturbation-contract shape (Phase 8),
    computed from real measured single-cell data, not simulated.
    """

    name = "scperturb"
    conformance_curie = "scperturb:DixitRegev2016_K562_TFs_13_days:p-sgIRF1-2"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "scperturb"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, local_id = parse_curie(curie)
        dataset_key, _, perturbation_label = local_id.partition(":")
        if dataset_key not in _KNOWN_DATASETS:
            raise UnknownScPerturbDatasetError(
                f"'{dataset_key}' is not registered; known datasets: {sorted(_KNOWN_DATASETS)}"
            )

        h5ad_path = cached_download(_ZENODO_RECORD.format(filename=_KNOWN_DATASETS[dataset_key]))
        adata = ad.read_h5ad(h5ad_path)

        perturbed_mask = (adata.obs["perturbation"] == perturbation_label).to_numpy()
        control_mask = (adata.obs["perturbation"] == "control").to_numpy()
        if perturbed_mask.sum() == 0:
            raise ValueError(f"no cells found with perturbation == '{perturbation_label}'")

        expression = adata.X.tocsr() if sp.issparse(adata.X) else sp.csr_matrix(adata.X)
        mean_perturbed = _normalized_mean(expression, perturbed_mask)
        mean_control = _normalized_mean(expression, control_mask)
        delta = mean_perturbed - mean_control

        top_indices = np.argsort(-np.abs(delta))[:_TOP_N_GENES]
        gene_names = adata.var_names.to_numpy()

        # If this dataset records an explicit CRISPR target gene for the
        # perturbation (real metadata, not parsed from the label string),
        # report its own delta directly — a much more direct sanity check
        # ("did knocking down gene X reduce gene X's own expression?")
        # than hoping it happens to land in the top-N by magnitude.
        target_gene = None
        target_gene_delta = None
        if "target" in adata.obs.columns:
            targets = adata.obs.loc[perturbed_mask, "target"].unique()
            if len(targets) == 1 and targets[0] in gene_names:
                target_gene = str(targets[0])
                target_gene_delta = float(delta[gene_names == targets[0]][0])

        return {
            "curie": curie,
            "source": "scPerturb (harmonized Perturb-seq)",
            "license": "CC BY 4.0 (per-study terms may vary — verify before redistribution)",
            "data": {
                "dataset_key": dataset_key,
                "perturbation_label": perturbation_label,
                "perturbation_type": str(adata.obs["perturbation_type"].iloc[0]),
                "target_gene": target_gene,
                "target_gene_self_delta": target_gene_delta,
                "n_perturbed_cells": int(perturbed_mask.sum()),
                "n_control_cells": int(control_mask.sum()),
                "top_gene_deltas": {
                    gene_names[i]: float(delta[i]) for i in top_indices
                },
            },
        }


def _normalized_mean(expression: sp.csr_matrix, mask: np.ndarray) -> np.ndarray:
    """Total-count normalize (to 1e4) then log1p — the standard, minimal
    single-cell normalization, applied here manually (no scanpy
    dependency) since it's a two-line operation on a sparse matrix.
    """
    subset = expression[mask]
    counts_per_cell = np.asarray(subset.sum(axis=1)).flatten()
    counts_per_cell[counts_per_cell == 0] = 1
    normalized = subset.multiply(1.0 / counts_per_cell[:, None]).tocsr() * 1e4
    normalized = normalized.copy()
    normalized.data = np.log1p(normalized.data)
    return np.asarray(normalized.mean(axis=0)).flatten()
