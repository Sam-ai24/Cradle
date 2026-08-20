from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CurationError(AssertionError):
    """Raised when a model is promoted to 'curated' without meeting the bar."""


@dataclass
class CurationRecord:
    """Cradle's own curated/non-curated tiering (Architecture, Layer 8),
    mirroring BioModels' two-tier trust model: a model is only "curated"
    once independently reproduced against its source and MIRIAM-annotated
    — not just imported.
    """

    model_curie: str
    title: str
    tier: str
    evidence: list[str]
    adapters_used: list[str]
    verified_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def promote_to_curated(
    model_curie: str,
    title: str,
    evidence_checks: dict[str, bool],
    adapters_used: list[str],
) -> CurationRecord:
    """Build a "curated" record — but only if every named evidence check
    actually passed. This is the mechanical gate behind Layer 8's rule:
    curation status is earned by passing checks, not assigned by a flag.
    """
    failed = [name for name, passed in evidence_checks.items() if not passed]
    if failed:
        raise CurationError(
            f"cannot promote '{model_curie}' to curated — failed checks: {', '.join(failed)}"
        )
    if len(adapters_used) < 2:
        raise CurationError(
            f"cannot promote '{model_curie}' to curated — reproduced on only "
            f"{len(adapters_used)} adapter(s), need at least 2 independent ones"
        )
    return CurationRecord(
        model_curie=model_curie,
        title=title,
        tier="curated",
        evidence=list(evidence_checks.keys()),
        adapters_used=adapters_used,
    )


def write_curation_record(record: CurationRecord, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    return path


def read_curation_record(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
