from __future__ import annotations

import pytest

from cradle.substrate import archive, experiment, model, provenance
from cradle.substrate.examples.toggle_switch import build_annotated_document

te = pytest.importorskip(
    "tellurium", reason="tellurium is a Phase 1 demo-only dependency (pip install -e .[demo])"
)

SPECIES_IDS = ["U", "V"]
KISAO_ID = "KISAO:0000019"  # CVODE
OUTPUT_END_TIME = 10.0
NUMBER_OF_STEPS = 50


@pytest.fixture()
def roundtrip_paths(tmp_path):
    return {
        "sbml": str(tmp_path / "toggle_switch.xml"),
        "sedml": str(tmp_path / "experiment.xml"),
        "archive": str(tmp_path / "toggle_switch.omex"),
        "provenance": str(tmp_path / "toggle_switch.provenance.json"),
    }


def test_antimony_to_sbml_round_trip_is_fully_annotated():
    document = build_annotated_document()
    sbml_model = document.getModel()
    for entity in (
        list(sbml_model.getListOfSpecies())
        + list(sbml_model.getListOfParameters())
        + list(sbml_model.getListOfReactions())
    ):
        assert entity.getNumCVTerms() > 0, f"{entity.getId()} has no CURIE annotation"


def test_full_substrate_round_trip_executes_and_reproduces(roundtrip_paths):
    # Antimony -> SBML (annotated)
    document = build_annotated_document()
    model.write_sbml(document, roundtrip_paths["sbml"])

    # SED-ML: describe a uniform time course over the SBML model
    sedml_doc = experiment.build_uniform_time_course_sedml(
        "toggle_switch.xml",
        SPECIES_IDS,
        kisao_id=KISAO_ID,
        output_end_time=OUTPUT_END_TIME,
        number_of_steps=NUMBER_OF_STEPS,
    )
    experiment.write_sedml(sedml_doc, roundtrip_paths["sedml"])

    # COMBINE archive: bundle both
    archive.package_combine_archive(
        roundtrip_paths["archive"],
        roundtrip_paths["sbml"],
        "toggle_switch.xml",
        roundtrip_paths["sedml"],
        "experiment.xml",
    )

    # Execute: run the archive end to end via Tellurium/libRoadRunner (the
    # engine Phase 2 formalizes behind the SimulationAdapter contract)
    results = te.executeCombineArchive(roundtrip_paths["archive"], createOutputs=True)
    assert results, "executeCombineArchive returned no results"

    data_generators = next(iter(results.values()))["dataGenerators"]
    assert "dg_time" in data_generators
    assert "dg_U" in data_generators and "dg_V" in data_generators
    assert len(data_generators["dg_time"]) == NUMBER_OF_STEPS + 1

    # The toggle switch should settle near one of its two stable steady
    # states (U high/V low or U low/V high), not stay at the unstable
    # midpoint it started near.
    final_u = data_generators["dg_U"][-1][0]
    final_v = data_generators["dg_V"][-1][0]
    assert abs(final_u - final_v) > 5, (
        f"expected the switch to resolve toward one stable state, got U={final_u}, V={final_v}"
    )

    # Provenance: log what actually ran, alongside the archive
    record = provenance.RunProvenance(
        combine_archive=roundtrip_paths["archive"],
        sbml_model_source="toggle_switch.xml",
        sedml_experiment_source="experiment.xml",
        model_curies=["biomodels.db:BIOMD0000000507", "doi:10.1038/35002131"],
        kisao_id=KISAO_ID,
        algorithm_name="CVODE",
        initial_time=0.0,
        output_start_time=0.0,
        output_end_time=OUTPUT_END_TIME,
        number_of_steps=NUMBER_OF_STEPS,
        engine_name="tellurium/libRoadRunner",
        engine_version=te.getTelluriumVersion(),
        output_variable_ids=["time", *SPECIES_IDS],
    )
    provenance.write_provenance(record, roundtrip_paths["provenance"])

    reloaded = provenance.read_provenance(roundtrip_paths["provenance"])
    assert reloaded["kisao_id"] == KISAO_ID
    assert reloaded["curated_tier"] == "non-curated"
    assert set(reloaded["model_curies"]) == {
        "biomodels.db:BIOMD0000000507",
        "doi:10.1038/35002131",
    }
