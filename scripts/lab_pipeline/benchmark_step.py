"""Phase 11 CWL pipeline, step 4: benchmark.

    python benchmark_step.py --results result_tellurium.json result_copasi.json \
        --species U --tolerance 0.01 --output benchmark.json

Cross-engine agreement is the actual proof the swap boundary works
(Phase 2/4's own exit criteria) — reused here via
`cradle.lab.compare_trajectories` rather than a new comparison written
just for the pipeline. Exits non-zero if any pair disagrees past
`--tolerance`, so a CI-style pipeline run can fail loudly on real drift.
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
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--species", required=True)
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = {}
    for result_path in args.results:
        result = json.loads(Path(result_path).read_text(encoding="utf-8"))
        results[result["engine"]] = result

    disagreements = lab.compare_trajectories(results, args.species)
    within_tolerance = all(value <= args.tolerance for value in disagreements.values())

    report = {
        "species": args.species,
        "tolerance": args.tolerance,
        "disagreements": disagreements,
        "within_tolerance": within_tolerance,
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}: {report}")

    return 0 if within_tolerance else 1


if __name__ == "__main__":
    sys.exit(main())
