from __future__ import annotations

from typing import Any

import tellurium as te

from cradle.contracts.simulation_adapter import SimulationResult


class TelluriumSimulationAdapter:
    """Wraps Tellurium/libRoadRunner behind the SimulationAdapter contract.

    Executes the SED-ML task described inside a COMBINE archive
    (Architecture, Layer 4) via Tellurium's own native COMBINE-archive
    executor, which handles the model/experiment parsing internally rather
    than needing a hand-rolled SED-ML interpretation (contrast with the
    COPASI adapter, whose native SED-ML importer proved unreliable).
    """

    name = "tellurium"
    input_mode = "combine_archive"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        archive_path = model["combine_archive"]
        results = te.executeCombineArchive(archive_path, createOutputs=True)
        report = next(iter(results.values()))
        data_generators = report["dataGenerators"]

        time_values = [row[0] for row in data_generators["dg_time"]]
        trajectories = {
            key[len("dg_") :]: [row[0] for row in values]
            for key, values in data_generators.items()
            if key.startswith("dg_") and key != "dg_time"
        }
        return {"t": time_values, "trajectories": trajectories, "engine": self.name}
