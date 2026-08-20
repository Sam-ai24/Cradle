"""Phase 11 CWL pipeline, step 2: apply.

    python apply_step.py --sbml-in model.xml \
        --estimation-report estimation_report.json --sbml-out model_fitted.xml

Reconstructs the `EstimationReport` dataclass `fit_step.py` serialized to
JSON, then delegates to `cradle.lab.apply_fitted_parameters` — the same
function `tests/test_lab_api.py` already exercises directly, so this
script adds only argument parsing and JSON (de)serialization, no new logic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from cradle import lab  # noqa: E402
from cradle.estimation import EstimationReport, ParameterEstimate  # noqa: E402


def _load_estimation_report(path: str) -> EstimationReport:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EstimationReport(
        model_source=data["model_source"],
        engine=data["engine"],
        optimization_method=data["optimization_method"],
        objective_value=data["objective_value"],
        data_points=data["data_points"],
        parameters=[ParameterEstimate(**p) for p in data["parameters"]],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbml-in", required=True)
    parser.add_argument("--estimation-report", required=True)
    parser.add_argument("--sbml-out", required=True)
    args = parser.parse_args()

    report = _load_estimation_report(args.estimation_report)
    lab.apply_fitted_parameters(args.sbml_in, args.sbml_out, report)
    print(f"Wrote {args.sbml_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
