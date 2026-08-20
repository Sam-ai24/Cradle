from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RunProvenance:
    """Minimal MIASE-compliant provenance record for one Cradle simulation run.

    Captures what MIASE (Minimum Information About a Simulation Experiment)
    asks for: which model, what modifications were made to it, which
    simulation setting and numerical algorithm were used, and what outputs
    were produced — serialized alongside the COMBINE archive so a run is
    machine-reproducible rather than only described in prose (Architecture,
    Layer 8).
    """

    combine_archive: str
    sbml_model_source: str
    sedml_experiment_source: str
    model_curies: list[str]
    kisao_id: str
    algorithm_name: str
    initial_time: float
    output_start_time: float
    output_end_time: float
    number_of_steps: int
    engine_name: str
    engine_version: str
    output_variable_ids: list[str]
    curated_tier: str = "non-curated"
    model_modifications: list[str] = field(default_factory=list)
    run_timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_provenance(record: RunProvenance, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    return path


def read_provenance(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
