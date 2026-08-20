"""Phase 11: build the example inputs the lab pipeline (CWL/Snakemake) runs
against by default.

    python scripts/lab_pipeline/prepare_example_inputs.py

Writes workflows/example_input/{model.xml,observed_data.json,fit_spec.json}.
Same real model and same "synthetic data generated at a known ground truth"
pattern Phase 6's `tests/test_parameter_estimation.py` already established
(alpha1 = 156.25, the real Gardner, Cantor & Collins 2000 fitted value) —
not a new invented example, just the one already-verified case made runnable
as a pipeline input instead of only a pytest fixture.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import numpy as np  # noqa: E402

from cradle.substrate import model as cmodel  # noqa: E402
from cradle.substrate.examples.toggle_switch import build_annotated_document  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "workflows" / "example_input"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sbml_path = OUTPUT_DIR / "model.xml"
    cmodel.write_sbml(build_annotated_document(), str(sbml_path))

    import basico

    copasi_model = basico.load_model(str(sbml_path))
    trajectory = basico.run_time_course(0, 2.0, 20, model=copasi_model, method="deterministic")

    rng = np.random.default_rng(42)
    noisy_u = (trajectory["U"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))).tolist()
    noisy_v = (trajectory["V"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))).tolist()

    (OUTPUT_DIR / "observed_data.json").write_text(
        json.dumps({"time": trajectory.index.tolist(), "U": noisy_u, "V": noisy_v}, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "fit_spec.json").write_text(
        json.dumps(
            [{"name": "Values[alpha1]", "lower": 1.0, "upper": 500.0, "start": 50.0}], indent=2
        ),
        encoding="utf-8",
    )
    print(f"Wrote example inputs to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
