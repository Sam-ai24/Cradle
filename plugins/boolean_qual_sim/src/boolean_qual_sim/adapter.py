from __future__ import annotations

from typing import Any

from cradle.contracts.simulation_adapter import SimulationResult
from cradle.qual import read_qual_model


class BooleanQualSimulationAdapter:
    """SBML-qual Boolean/qualitative gene-regulatory-network execution
    (Architecture, Layer 1/4). No mature registered engine executes SBML
    `qual` the way COPASI/Tellurium execute continuous kinetics, so this
    adapter is Cradle's own — a synchronous Boolean-network update
    (`cradle.qual.QualModel.step`), the standard convention for this model
    class, implemented directly rather than depending on GINsim (Java) or
    BoolNet (R), both of which would introduce a second-language runtime
    for a genuinely simple update rule.
    """

    name = "boolean-qual"
    input_mode = "qual_sbml"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        qual_model = read_qual_model(model["sbml_path"])
        n_steps = config.get("n_steps", 10)

        levels = qual_model.initial_levels()
        trajectories: dict[str, list[float]] = {sid: [levels[sid]] for sid in levels}
        for step in range(n_steps):
            levels = qual_model.step(levels)
            for species_id, level in levels.items():
                trajectories[species_id].append(float(level))

        return {
            "t": [float(i) for i in range(n_steps + 1)],
            "trajectories": trajectories,
            "engine": self.name,
        }
