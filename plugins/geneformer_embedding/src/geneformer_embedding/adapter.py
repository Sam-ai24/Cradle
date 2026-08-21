"""Phase 12 continued: Geneformer, the embedding model Architecture Layer 5's
own table has named as the intended default since Phase 5 — never built
until now, because getting a real, working install was a genuinely
multi-step problem, not a `pip install geneformer` (confirmed: no PyPI
package exists under that name).

Real, disclosed friction, worked around rather than hidden:
- Geneformer ships only from its HuggingFace repo
  (`ctheodoris/Geneformer`), as source files + pickled dictionaries
  alongside the model weights, not a normal PyPI/git-installable package.
  `pip install git+https://huggingface.co/ctheodoris/Geneformer.git`
  fails on this machine (`fatal: expected 'packfile'` — a real, confirmed
  git/LFS partial-clone incompatibility, not assumed). Fetching the exact
  same files via `huggingface_hub.snapshot_download` instead works
  cleanly and resolves real LFS content directly, with no git involved.
- The package's own `geneformer/__init__.py` eagerly imports
  `emb_extractor`/`classifier`/`mtl_classifier` at package-import time,
  none of which this adapter needs (only `tokenizer.TranscriptomeTokenizer`
  is used; embeddings are extracted by loading the base model directly
  via `transformers`, the same pattern `esmc_embedding` already uses).
  Those three submodules import `tdigest`, whose own dependency
  `accumulation-tree` is a Cython extension that fails to build on this
  machine (`Microsoft Visual C++ 14.0 or greater is required`) — a real,
  confirmed native-toolchain gap, the same class of blocker Phase 12 hit
  building HADDOCK3/CellOracle. Rather than fabricate a `tdigest` stub
  whose semantics were never verified, this adapter fetches the package
  source into a local, sandboxed copy and replaces just `__init__.py`
  with a minimal version that imports only what's actually needed —
  disclosed here, not hidden, the same category as Phase 11's `pwd.py`
  stub.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Same real Windows/huggingface_hub symlink-privilege issue Phase 12 first
# hit building esmc_embedding — set before huggingface_hub is imported.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

import torch  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from transformers import AutoModel  # noqa: E402

from cradle.contracts.ai_model_adapter import ModelPrediction  # noqa: E402

HF_REPO = "ctheodoris/Geneformer"
MODEL_SUBFOLDER = "Geneformer-V1-10M"

#: Where the sandboxed, patched copy of the `geneformer` package source
#: lives — same cache-directory convention as `cradle.knowledge.cache`,
#: kept separate here since that helper is keyed for single-file
#: downloads, not a package snapshot.
_SRC_CACHE_DIR = Path.home() / ".cradle" / "cache" / "geneformer_src"

#: A minimal, hand-written replacement for the real `geneformer/__init__.py`
#: (see module docstring) — keeps only the file-path constants and the
#: `tokenizer` submodule, dropping the three submodules that transitively
#: require the unbuildable `tdigest`/`accumulation-tree` chain and aren't
#: needed for tokenization or base-model embedding extraction.
_PATCHED_INIT_PY = '''# Patched by Cradle's geneformer_embedding plugin - not the original
# upstream __init__.py. See geneformer_embedding/adapter.py's module
# docstring for exactly why and what was removed.
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*The 'nopython' keyword.*")

GENE_MEDIAN_FILE = Path(__file__).parent / "gene_median_dictionary_gc104M.pkl"
TOKEN_DICTIONARY_FILE = Path(__file__).parent / "token_dictionary_gc104M.pkl"
ENSEMBL_DICTIONARY_FILE = Path(__file__).parent / "gene_name_id_dict_gc104M.pkl"
ENSEMBL_MAPPING_FILE = Path(__file__).parent / "ensembl_mapping_dict_gc104M.pkl"

GENE_MEDIAN_FILE_30M = Path(__file__).parent / "gene_dictionaries_30m/gene_median_dictionary_gc30M.pkl"
TOKEN_DICTIONARY_FILE_30M = Path(__file__).parent / "gene_dictionaries_30m/token_dictionary_gc30M.pkl"
ENSEMBL_DICTIONARY_FILE_30M = Path(__file__).parent / "gene_dictionaries_30m/gene_name_id_dict_gc30M.pkl"
ENSEMBL_MAPPING_FILE_30M = Path(__file__).parent / "gene_dictionaries_30m/ensembl_mapping_dict_gc30M.pkl"

from . import tokenizer
from .tokenizer import TranscriptomeTokenizer
'''

_SOURCE_FILE_PATTERNS = [
    "geneformer/*.py",
    "geneformer/gene_dictionaries_30m/*",
    "geneformer/*.pkl",
]


def _ensure_geneformer_source() -> None:
    """Fetch (once, cached) a sandboxed copy of the real `geneformer`
    package source + dictionaries via `huggingface_hub` directly - no git,
    no pip package - then overwrite its `__init__.py` with the minimal
    patched version above, and put the sandbox ahead of `sys.path` so
    `import geneformer` resolves to this patched copy.
    """
    init_path = _SRC_CACHE_DIR / "geneformer" / "__init__.py"
    if not init_path.exists():
        snapshot_download(
            repo_id=HF_REPO,
            allow_patterns=_SOURCE_FILE_PATTERNS,
            local_dir=str(_SRC_CACHE_DIR),
        )
        init_path.write_text(_PATCHED_INIT_PY, encoding="utf-8")

    if str(_SRC_CACHE_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_CACHE_DIR))


_ensure_geneformer_source()

from geneformer import TranscriptomeTokenizer  # noqa: E402

_model = None  # lazy singleton, same pattern as esmc_embedding


def _get_model():
    global _model
    if _model is None:
        _model = AutoModel.from_pretrained(HF_REPO, subfolder=MODEL_SUBFOLDER)
        _model.eval()
    return _model


def _example_h5ad_path() -> str:
    """A real, small, cached example input: the first 20 cells of
    scanpy's `pbmc3k` (10x Genomics' classic real human-PBMC dataset,
    not synthetic), reshaped to Geneformer's documented input schema
    (`var["ensembl_id"]`, `obs["n_counts"]`). Built once, cached - the
    same "large-ish one-time real download, cached" pattern Phase 8
    established, just for a derived file rather than a raw source file.
    """
    cache_path = Path.home() / ".cradle" / "cache" / "geneformer_pbmc3k_example.h5ad"
    if not cache_path.exists():
        import scanpy as sc

        adata = sc.datasets.pbmc3k()[:20].copy()
        adata.var["ensembl_id"] = adata.var["gene_ids"]
        adata.obs["n_counts"] = adata.X.sum(axis=1)
        adata.obs["filter_pass"] = 1
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        adata.write_h5ad(cache_path)
    return str(cache_path)


class GeneformerEmbeddingAdapter:
    """Embedding AI contract (Architecture, Layer 5): a single-cell
    RNA-seq h5ad file in, one embedding vector per cell out - mean-pooled
    over Geneformer's real per-gene-token hidden states (excluding
    padding), the same "load the base model, mean-pool last_hidden_state"
    approach `esmc_embedding` already uses for protein sequences. This is
    a genuinely different embedding domain (single-cell transcriptomes,
    not protein sequences) - the actual model Architecture Layer 5's own
    table named as the intended embedding-contract default since Phase 5.
    """

    name = "geneformer-v1-10m"
    contract_type = "embedding"

    @property
    def conformance_input(self) -> dict[str, Any]:
        return {"h5ad_path": _example_h5ad_path()}

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        h5ad_path = input["h5ad_path"]
        model = _get_model()

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "in"
            output_dir = Path(tmp_dir) / "out"
            input_dir.mkdir()
            # TranscriptomeTokenizer reads every *.h5ad file in a directory,
            # not a single file path - stage this one input into its own
            # scratch directory rather than pointing it at h5ad_path's
            # (possibly shared) parent, which could contain unrelated files.
            staged_path = input_dir / "input.h5ad"
            staged_path.write_bytes(Path(h5ad_path).read_bytes())

            tokenizer = TranscriptomeTokenizer({}, nproc=1, model_version="V1")
            tokenizer.tokenize_data(str(input_dir), str(output_dir), "tokenized", file_format="h5ad")

            from datasets import load_from_disk

            dataset = load_from_disk(str(output_dir / "tokenized.dataset"))

        embeddings = []
        with torch.no_grad():
            for cell in dataset:
                input_ids = torch.tensor([cell["input_ids"]])
                last_hidden = model(input_ids=input_ids).last_hidden_state
                pooled = last_hidden[0].mean(dim=0)
                embeddings.append(pooled.tolist())

        return {
            "output": {
                "embeddings": embeddings,
                "embedding_dim": model.config.hidden_size,
                "n_cells": len(embeddings),
            },
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "hf_repo": HF_REPO,
                "hf_subfolder": MODEL_SUBFOLDER,
                "license": "Apache-2.0 (HfApi().model_info().gated == False, "
                "license:apache-2.0 tag)",
                "pooling": "mean_over_gene_tokens_excluding_padding",
                "tokenizer_model_version": "V1",
            },
        }


def build_adapter() -> GeneformerEmbeddingAdapter:
    return GeneformerEmbeddingAdapter()
