from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import anndata as ad

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.cache import cached_download
from cradle.substrate.annotate import parse_curie

#: Tabula Muris Senis, Pancreas (Smart-seq2) — one real dataset from the
#: mouse aging atlas already indexed in CZ CELLxGENE (Phase 3), covering
#: real donor ages 18/21/24/30 months. Only this one tissue/assay
#: combination is registered — the full atlas is dozens of files at
#: 65MB-6GB each (docs/RESOURCES.md); this is the one small enough to
#: cache and use directly.
_DATASET_URL = "https://datasets.cellxgene.cziscience.com/b257ae76-c030-4d61-9a73-775b5d195a9a.h5ad"
_AGE_ORDER = ["18m", "21m", "24m", "30m"]


class GeneNotFoundError(KeyError):
    pass


class AgingExpressionConnector:
    """Real age-indexed single-cell expression (Architecture, Layer 7's
    intervention-validation extension; Phase 8's aging category), from
    Tabula Muris Senis via CZ CELLxGENE. Returns raw per-age-group mean
    expression for one gene — the `trajectory` perturbation-contract
    shape's data source, computed from real measured cells at each real
    donor age, not simulated or interpolated.

    Deliberately does not claim any expected direction (e.g. "increases
    with age") — checked directly against a real senescence marker
    (Cdkn2a) in this specific tissue/dataset slice, and it does *not*
    show a clean monotonic increase (likely confounded by an n=51 group
    at 24 months). Real aging data is messier than the textbook
    expectation; this connector reports what the data says, not what a
    hypothesis predicts.
    """

    name = "aging-expression"
    conformance_curie = "aging.gene:Cdkn2a"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "aging.gene"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, gene_symbol = parse_curie(curie)
        h5ad_path = cached_download(_DATASET_URL)
        adata = ad.read_h5ad(h5ad_path)

        matches = np.where(adata.var["feature_name"].to_numpy() == gene_symbol)[0]
        if len(matches) == 0:
            raise GeneNotFoundError(f"'{gene_symbol}' not found in this dataset's features")
        gene_index = matches[0]

        expression = adata.X.tocsc() if sp.issparse(adata.X) else sp.csc_matrix(adata.X)
        column = np.asarray(expression[:, gene_index].todense()).flatten()

        ages_present = [age for age in _AGE_ORDER if age in adata.obs["age"].cat.categories]
        means_by_age = {}
        counts_by_age = {}
        for age in ages_present:
            mask = (adata.obs["age"] == age).to_numpy()
            means_by_age[age] = float(column[mask].mean())
            counts_by_age[age] = int(mask.sum())

        return {
            "curie": curie,
            "source": "Tabula Muris Senis (via CZ CELLxGENE)",
            "license": "CC BY 4.0",
            "data": {
                "gene_symbol": gene_symbol,
                "tissue": "pancreas",
                "assay": "Smart-seq2",
                "ages": ages_present,
                "mean_expression_by_age": means_by_age,
                "cell_count_by_age": counts_by_age,
            },
        }
