from __future__ import annotations

from pathlib import Path

from cradle.md import BondSpec, IntegratorSpec, MDManifest, NonbondedSpec, ParticleSpec, write_manifest
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


#: A tiny coarse-grained bead-spring chain — the reference fixture for any
#: SimulationAdapter declaring `input_mode = "md_manifest"`. Short enough
#: (2000 steps) to conformance-test quickly; too short to expect tight
#: thermal equilibration, which is what the dedicated correctness test
#: (not this conformance fixture) checks over a longer run.
REFERENCE_MD_PARTICLE_COUNT = 4


def build_reference_md_manifest(destination_dir: str) -> str:
    manifest = MDManifest(
        particles=[
            ParticleSpec(mass_amu=12.0, position_nm=(i * 0.5, 0.0, 0.0))
            for i in range(REFERENCE_MD_PARTICLE_COUNT)
        ],
        bonds=[
            BondSpec(particle_i=i, particle_j=i + 1, length_nm=0.5, force_constant_kj_per_nm2=500.0)
            for i in range(REFERENCE_MD_PARTICLE_COUNT - 1)
        ],
        nonbonded=NonbondedSpec(sigma_nm=0.4, epsilon_kj_per_mol=0.5),
        integrator=IntegratorSpec(
            kind="langevin_middle", temperature_k=300.0, friction_per_ps=1.0, timestep_ps=0.002
        ),
        n_steps=2000,
        report_interval=200,
    )
    path = str(Path(destination_dir) / "md_manifest.json")
    write_manifest(manifest, path)
    return path
