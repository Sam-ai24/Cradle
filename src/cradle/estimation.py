from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParameterEstimate:
    """One fitted parameter's value *and* its uncertainty — Architecture,
    Layer 8: "uncertainty as a first-class output... never a point
    estimate presented without a confidence/identifiability diagnostic."

    `std_dev` and the confidence interval here are a Wald-type (local,
    Fisher-information-based) approximation — what COPASI's parameter
    estimation statistics report from the optimum's Hessian — not a full
    profile-likelihood scan. That's a real distinction: Wald intervals can
    be misleading for parameters with skewed or multimodal likelihood
    surfaces, where a true profile-likelihood scan would catch what this
    approximation can miss. Good enough to guarantee every fitted
    parameter reports *some* identifiability diagnostic rather than a
    bare number; not a substitute for a full profile-likelihood pass on a
    parameter you have reason to suspect is poorly identified.
    """

    name: str
    fitted_value: float
    std_dev: float
    lower_95ci: float
    upper_95ci: float
    coefficient_of_variation: float
    method: str = "wald_local"


@dataclass
class EstimationReport:
    model_source: str
    engine: str
    optimization_method: str
    objective_value: float
    data_points: int
    parameters: list[ParameterEstimate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_estimation_report(report: EstimationReport, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path


def read_estimation_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
