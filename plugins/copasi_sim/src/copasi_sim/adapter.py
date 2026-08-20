from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import basico

from cradle.contracts.simulation_adapter import SimulationResult
from cradle.substrate.archive import extract_combine_archive
from cradle.substrate.experiment import read_uniform_time_course_spec


class CopasiSimulationAdapter:
    """Wraps COPASI (via `basico`) behind the SimulationAdapter contract.

    COPASI's own SED-ML importer (`COPASI.SEDMLImporter`) did not reliably
    reproduce the described time course in testing — it imported the model
    but silently fell back to default trajectory-task settings instead of
    the SED-ML document's actual duration/step count. This adapter instead
    parses the SED-ML uniform time course itself via
    `cradle.substrate.experiment` and drives basico's own simulation API
    directly: the same "parse the standard, drive the engine natively"
    pattern a BioSimulators wrapper uses, chosen here because trusting
    COPASI's own importer proved unreliable, not as a shortcut.
    """

    name = "copasi"
    input_mode = "combine_archive"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        archive_path = model["combine_archive"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            sedml_path = extract_combine_archive(archive_path, tmp_dir)
            spec = read_uniform_time_course_spec(sedml_path)
            sbml_path = str(Path(sedml_path).parent / spec.model_source)

            copasi_model = basico.load_model(sbml_path)
            data_frame = basico.run_time_course(
                spec.output_start_time,
                spec.output_end_time - spec.initial_time,
                spec.number_of_steps,
                model=copasi_model,
                method="deterministic",
            )

        trajectories = {
            species_id: data_frame[species_id].tolist()
            for species_id in spec.reported_species_ids
        }
        return {
            "t": data_frame.index.tolist(),
            "trajectories": trajectories,
            "engine": self.name,
        }
