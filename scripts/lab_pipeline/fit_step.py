"""Phase 11 CWL pipeline, step 1: fit.

    python fit_step.py --sbml model.xml --observed-data data.json \
        --fit-spec fit_spec.json --output estimation_report.json

`--observed-data` is a JSON object `{"time": [...], "<species_id>": [...], ...}`.
`--fit-spec` is a JSON array of `{"name", "lower", "upper", "start"}` objects
(COPASI global-quantity names, e.g. "Values[alpha1]" — see
`cradle.lab.fit_parameter`'s docstring).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from cradle import lab  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbml", required=True)
    parser.add_argument("--observed-data", required=True)
    parser.add_argument("--fit-spec", required=True)
    parser.add_argument("--method", default="Levenberg - Marquardt")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    observed_data = json.loads(Path(args.observed_data).read_text(encoding="utf-8"))
    fit_spec = json.loads(Path(args.fit_spec).read_text(encoding="utf-8"))

    report = lab.fit_parameter(args.sbml, fit_spec, observed_data, method=args.method)
    Path(args.output).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
