"""Phase 11 CWL pipeline, step 3: simulate.

    python simulate_step.py --sbml model_fitted.xml --species U V \
        --adapter tellurium --end-time 2.0 --steps 20 --output result_tellurium.json

Packages `--sbml` into a fresh COMBINE archive (SED-ML uniform time course
over `--species`) and runs it on the named registered SimulationAdapter —
the same two real, already-registered Phase 2 plugins every other Cradle
test uses, not a new execution path.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from cradle import lab  # noqa: E402
from cradle.substrate import archive, experiment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbml", required=True)
    parser.add_argument("--species", nargs="+", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--end-time", type=float, default=2.0)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        sbml_name = "model.xml"
        sbml_path = str(Path(tmp_dir) / sbml_name)
        shutil.copyfile(args.sbml, sbml_path)

        sedml_doc = experiment.build_uniform_time_course_sedml(
            sbml_name, args.species, output_end_time=args.end_time, number_of_steps=args.steps
        )
        sedml_path = str(Path(tmp_dir) / "experiment.xml")
        experiment.write_sedml(sedml_doc, sedml_path)

        archive_path = str(Path(tmp_dir) / "run.omex")
        archive.package_combine_archive(archive_path, sbml_path, sbml_name, sedml_path, "experiment.xml")

        result = lab.simulate(archive_path, args.adapter)

    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
