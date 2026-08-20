from __future__ import annotations

from pathlib import Path

from cradle.substrate import archive, experiment, model
from cradle.substrate.examples import toy_fba
from cradle.substrate.examples.toggle_switch import build_annotated_document

#: The Phase 1 toggle-switch model, reused as the canonical fixture for
#: conformance-testing any SimulationAdapter that declares
#: `input_mode = "combine_archive"`, rather than inventing a second one.
REFERENCE_SPECIES_IDS = ["U", "V"]
REFERENCE_OUTPUT_END_TIME = 10.0
REFERENCE_NUMBER_OF_STEPS = 50


def build_reference_combine_archive(destination_dir: str) -> str:
    destination = Path(destination_dir)
    sbml_path = str(destination / "toggle_switch.xml")
    sedml_path = str(destination / "experiment.xml")
    archive_path = str(destination / "toggle_switch.omex")

    document = build_annotated_document()
    model.write_sbml(document, sbml_path)

    sedml_doc = experiment.build_uniform_time_course_sedml(
        "toggle_switch.xml",
        REFERENCE_SPECIES_IDS,
        output_end_time=REFERENCE_OUTPUT_END_TIME,
        number_of_steps=REFERENCE_NUMBER_OF_STEPS,
    )
    experiment.write_sedml(sedml_doc, sedml_path)

    archive.package_combine_archive(
        archive_path, sbml_path, "toggle_switch.xml", sedml_path, "experiment.xml"
    )
    return archive_path


def build_reference_fba_sbml(destination_dir: str) -> str:
    """The synthetic toy FBA model, reused as the canonical fixture for
    conformance-testing any SimulationAdapter that declares
    `input_mode = "fba_sbml"`.
    """
    return toy_fba.write_sbml(str(Path(destination_dir) / "toy_fba.xml"))
