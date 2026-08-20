from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from cradle.contracts.simulation_adapter import SimulationResult


class CobraFbaAdapterError(RuntimeError):
    pass


class CobraFbaSimulationAdapter:
    """Wraps COBRApy behind the SimulationAdapter contract for constraint-
    based flux-balance analysis.

    COBRApy is GPL/LGPL (NOTICE.md) and runs subprocess-isolated: this
    adapter never imports `cobra` itself, only `cobrapy_fba.worker` in a
    child process, so GPL code never enters cradle-core's or another
    plugin's process. A production deployment would run the worker in its
    own container (Architecture, Layer 4/8); a subprocess is the minimal
    correct isolation for local development.

    FBA is a steady-state analysis, not a time course, so its result is
    represented as a length-1 "trajectory" — one snapshot of reaction
    fluxes — which keeps it a valid `SimulationResult` without forcing a
    time-course shape onto data that has no time axis.
    """

    name = "cobrapy"
    input_mode = "fba_sbml"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        sbml_path = model["sbml_path"]
        completed = subprocess.run(
            [sys.executable, "-m", "cobrapy_fba.worker", sbml_path],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise CobraFbaAdapterError(
                f"cobrapy_fba.worker failed (exit {completed.returncode}): {completed.stderr}"
            )

        payload = json.loads(completed.stdout)
        trajectories = {
            reaction_id: [flux] for reaction_id, flux in payload["fluxes"].items()
        }
        return {
            "t": [0.0],
            "trajectories": trajectories,
            "engine": self.name,
            "status": payload["status"],
            "objective_value": payload["objective_value"],
        }
