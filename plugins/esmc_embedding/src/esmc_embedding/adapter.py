"""Phase 12: the embedding AI contract, real for the first time.

Phase 5 defined the typed embedding contract but never implemented it —
Geneformer needed real GPU-scale weights and was deliberately deferred
rather than stubbed. Checked directly rather than assumed for Phase 12:
ESM Cambrian's 300M-parameter checkpoint
(`EvolutionaryScale/esmc-300m-2024-12`) is **not** license-gated on
HuggingFace (`HfApi().model_info(...).gated == False`, tags include
`license:mit`) — unlike the larger ESM3 checkpoints, which do carry
EvolutionaryScale's non-commercial Cambrian license and remain deferred
for that reason, same footing as Phase 5/7's other deferred heavy models.
ESM-C-300M's ~1.3GB weight download is a real, disclosed one-time cost
(cached by `huggingface_hub` afterward, same "large one-time download,
cached" pattern Phase 8 established for DepMap's bulk file) — confirmed
in this session to take ~110s once and ~8s to reload from cache, with
CPU inference itself taking under 2 seconds for a ~230-residue protein.
"""

from __future__ import annotations

import os
from typing import Any

# huggingface_hub's cache defaults to symlinks, which need
# SeCreateSymbolicLinkPrivilege on Windows (the same real blocker Phase 11
# hit with cwltool's file staging) — set *before* huggingface_hub is
# imported so a Windows researcher without Developer Mode enabled gets a
# graceful degraded (copy-based) cache instead of a crash, without needing
# to know this environment variable exists.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

from cradle.contracts.ai_model_adapter import ModelPrediction  # noqa: E402
from cradle.knowledge.http import get_json  # noqa: E402
from cradle.substrate.annotate import parse_curie  # noqa: E402

HF_REPO = "EvolutionaryScale/esmc-300m-2024-12"
_UNIPROT_SEQUENCE_API = "https://rest.uniprot.org/uniprotkb/{accession}.json"

#: A real, current, reviewed UniProt entry (human polyubiquitin-B
#: precursor) — small enough to embed in well under a second once the
#: model is loaded, used as this adapter's conformance probe.
CONFORMANCE_SEQUENCE = (
    "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
)

_model = None  # lazy singleton: load once per process, not once per predict() call


def _get_model():
    global _model
    if _model is None:
        from esm.models.esmc import ESMC

        _model = ESMC.from_pretrained("esmc_300m").to("cpu")
    return _model


def _resolve_sequence(input: dict[str, Any]) -> tuple[str, str]:
    """Returns (sequence, sequence_source) — `sequence_source` is either
    "direct" or the UniProt CURIE the sequence was resolved from, so
    provenance always states where the sequence came from.
    """
    if "sequence" in input:
        return input["sequence"], "direct"

    if "curie" in input:
        curie = input["curie"]
        namespace, accession = parse_curie(curie)
        if namespace != "uniprot":
            raise ValueError(
                f"esmc-300m can only resolve a sequence from a 'uniprot:' CURIE, got '{curie}'"
            )
        payload = get_json(_UNIPROT_SEQUENCE_API.format(accession=accession))
        sequence = payload.get("sequence", {}).get("value")
        if not sequence:
            raise ValueError(f"UniProt entry '{curie}' has no sequence (inactive/merged entry?)")
        return sequence, curie

    raise ValueError("esmc-300m's predict() input needs a 'sequence' or a 'curie' key")


class ESMCEmbeddingAdapter:
    """Embedding AI contract (Architecture, Layer 5): a protein sequence
    in, a fixed-length vector out — mean-pooled over the model's real
    per-residue embeddings (excluding the BOS/EOS special tokens), the
    standard way to get one whole-protein vector from a per-token model.
    """

    name = "esmc-300m"
    contract_type = "embedding"
    conformance_input = {"sequence": CONFORMANCE_SEQUENCE}

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        from esm.sdk.api import ESMProtein, LogitsConfig

        sequence, sequence_source = _resolve_sequence(input)
        model = _get_model()

        protein_tensor = model.encode(ESMProtein(sequence=sequence))
        logits_output = model.logits(
            protein_tensor, LogitsConfig(sequence=False, return_embeddings=True)
        )
        # embeddings shape is [1, len(sequence) + 2, d_model] — the +2 is
        # the BOS/EOS special tokens `encode()` adds; excluded from the
        # pool so they don't dilute the real per-residue signal.
        per_residue = logits_output.embeddings[0, 1:-1, :]
        pooled = per_residue.mean(dim=0)

        return {
            "output": {
                "embedding": pooled.tolist(),
                "embedding_dim": pooled.shape[0],
                "sequence_length": len(sequence),
            },
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "hf_repo": HF_REPO,
                "license": "MIT (confirmed 2026-08-21 via the model's own LICENSE.md and "
                "HfApi().model_info().gated == False — see docs/NOTICE.md's dated correction; "
                "this contradicted this project's own earlier, Phase 5-era assumption that "
                "ESM3/ESM-C were non-commercially licensed)",
                "pooling": "mean_over_residues_excluding_bos_eos",
                "sequence_source": sequence_source,
            },
        }


def build_adapter() -> ESMCEmbeddingAdapter:
    return ESMCEmbeddingAdapter()
