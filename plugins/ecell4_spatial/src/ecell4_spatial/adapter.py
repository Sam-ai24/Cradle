from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from cradle.contracts.simulation_adapter import SimulationResult


class ECell4WorkerError(RuntimeError):
    pass


class ECell4SpatialAdapter:
    """Particle-based spatial-stochastic tier (Architecture, Layer 4/9).

    Wraps E-Cell4's spatiocyte engine — chosen after CompuCell3D (conda-
    only, no PyPI path) and PhysiCell (C++-compile-only, no PyPI path)
    were both confirmed uninstallable, and after Smoldyn (also pip-
    installable) turned out to have a real, reproducible segmentation
    fault in this environment's build when retrieving molecule positions
    via its standard `listmols`/output-table mechanism — a serious native
    crash, not a missing feature, confirmed with the smallest possible
    reproduction (10 molecules, 10 timesteps) before it was ruled out.

    E-Cell4 is GPL-3.0 and runs subprocess-isolated (`ecell4_spatial.worker`,
    invoked as `python -m`), the same pattern as `cobrapy_fba` — GPL code
    never enters cradle-core's or another plugin's process.
    """

    name = "ecell4-spatiocyte"
    input_mode = "spatial_manifest"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        manifest_path = model["manifest_path"]
        completed = subprocess.run(
            [sys.executable, "-m", "ecell4_spatial.worker", manifest_path],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ECell4WorkerError(
                f"ecell4_spatial.worker failed (exit {completed.returncode}): {completed.stderr}"
            )

        payload = json.loads(completed.stdout)
        trajectories: dict[str, list[float]] = {}
        for species_name, stats in payload["species"].items():
            for stat_name, values in stats.items():
                trajectories[f"{species_name}_{stat_name}"] = values

        return {
            "t": payload["times"],
            "trajectories": trajectories,
            "engine": self.name,
        }
