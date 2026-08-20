from __future__ import annotations

import hashlib
from typing import Any

from cradle.contracts.ai_model_adapter import ModelPrediction


class HelloEmbeddingAdapter:
    """Trivial reference implementation of `cradle.contracts.AIModelAdapter`.

    Produces a deterministic pseudo-embedding from a hash of the input
    instead of running a real model. It exists only to prove the typed
    AI-contract/conformance mechanism works end to end, per Roadmap Phase 0.
    Phase 5 replaces this with real models (Geneformer, Evo2, OpenFold, ...)
    behind the identical `predict()` boundary.
    """

    name = "hello-ai"
    contract_type = "embedding"

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        digest = hashlib.sha256(repr(sorted(input.items())).encode()).digest()
        embedding = [b / 255 for b in digest[:8]]
        return {
            "output": embedding,
            "provenance": {"model": self.name, "contract_type": self.contract_type},
        }
