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
        gene_knockouts = config.get("gene_knockouts", [])
        completed = subprocess.run(
            [sys.executable, "-m", "cobrapy_fba.worker", sbml_path, *gene_knockouts],
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

    def _run_worker(self, *args: str, timeout: float | None = None) -> dict[str, Any]:
        completed = subprocess.run(
            [sys.executable, "-m", "cobrapy_fba.worker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise CobraFbaAdapterError(
                f"cobrapy_fba.worker failed (exit {completed.returncode}): {completed.stderr}"
            )
        if not completed.stdout.strip():
            raise CobraFbaAdapterError(
                f"cobrapy_fba.worker printed no JSON (stderr: {completed.stderr})"
            )
        return json.loads(completed.stdout)

    def gene_table(self, sbml_path: str) -> dict[str, Any]:
        """Dump every gene id/name/annotation from `sbml_path` in one
        subprocess — used to join FBA genes onto UniProt CURIEs and
        STRING preferred names without importing cobra in-process.
        """
        return self._run_worker("--gene-table", sbml_path, timeout=120)

    def single_gene_deletion(self, sbml_path: str) -> dict[str, Any]:
        """Genome-wide single-gene deletion in one subprocess: the model
        is loaded once and `cobra.flux_analysis.single_gene_deletion` runs
        with `processes=1`. Calling `run(..., gene_knockouts=[id])` once
        per gene would reload iML1515 ~1,500 times; this is the same
        science without that cost.
        """
        return self._run_worker("--single-gene-deletion", sbml_path, timeout=600)
