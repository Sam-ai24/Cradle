from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict, runtime_checkable

ContractType = Literal["embedding", "perturbation", "sequence", "structure", "orchestration"]


class ModelPrediction(TypedDict):
    output: Any
    provenance: dict[str, Any]


@runtime_checkable
class AIModelAdapter(Protocol):
    """Contract for a pluggable AI/foundation model (Architecture, Layer 5).

    Each adapter declares which of the five typed contracts it implements
    (embedding, perturbation, sequence, structure, orchestration) rather than
    exposing one generic "call the model" method — those contracts have
    genuinely different input/output shapes, so a single generic interface
    would hide real incompatibilities instead of surfacing them.
    """

    name: str
    contract_type: ContractType

    def predict(self, input: dict[str, Any]) -> ModelPrediction: ...
