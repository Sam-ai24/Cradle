from __future__ import annotations

import re
from dataclasses import dataclass

import libsedml

_SPECIES_TARGET_RE = re.compile(r"@id='([^']+)'")
_TIME_SYMBOL = "urn:sedml:symbol:time"


class ExperimentBuildError(RuntimeError):
    pass


def build_uniform_time_course_sedml(
    sbml_source_filename: str,
    species_ids: list[str],
    *,
    kisao_id: str = "KISAO:0000019",  # CVODE
    initial_time: float = 0.0,
    output_start_time: float = 0.0,
    output_end_time: float = 10.0,
    number_of_steps: int = 100,
) -> libsedml.SedDocument:
    """Build a SED-ML document describing a uniform time-course simulation of
    `sbml_source_filename`, reporting `species_ids` plus time.

    Per Architecture Layer 2, the algorithm is named via KiSAO
    (`kisao_id`) rather than any engine's native option string — this is
    the actual swap point that lets a different KiSAO-aware engine run the
    same document later.
    """
    doc = libsedml.SedDocument(1, 4)

    model = doc.createModel()
    model.setId("model1")
    model.setSource(sbml_source_filename)
    model.setLanguage("urn:sedml:language:sbml")

    sim = doc.createUniformTimeCourse()
    sim.setId("sim1")
    sim.setInitialTime(initial_time)
    sim.setOutputStartTime(output_start_time)
    sim.setOutputEndTime(output_end_time)
    sim.setNumberOfSteps(number_of_steps)
    algorithm = sim.createAlgorithm()
    algorithm.setKisaoID(kisao_id)

    task = doc.createTask()
    task.setId("task1")
    task.setModelReference("model1")
    task.setSimulationReference("sim1")

    report = doc.createReport()
    report.setId("report1")

    time_dg = doc.createDataGenerator()
    time_dg.setId("dg_time")
    time_var = time_dg.createVariable()
    time_var.setId("var_time")
    time_var.setTaskReference("task1")
    time_var.setSymbol("urn:sedml:symbol:time")
    if time_dg.setMath(libsedml.parseFormula("var_time")) != libsedml.LIBSEDML_OPERATION_SUCCESS:
        raise ExperimentBuildError("failed to set math for the time data generator")

    time_ds = report.createDataSet()
    time_ds.setId("ds_time")
    time_ds.setLabel("time")
    time_ds.setDataReference("dg_time")

    for species_id in species_ids:
        dg = doc.createDataGenerator()
        dg.setId(f"dg_{species_id}")
        var = dg.createVariable()
        var.setId(f"var_{species_id}")
        var.setTaskReference("task1")
        var.setTarget(
            f"/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='{species_id}']"
        )
        if dg.setMath(libsedml.parseFormula(f"var_{species_id}")) != libsedml.LIBSEDML_OPERATION_SUCCESS:
            raise ExperimentBuildError(f"failed to set math for data generator of '{species_id}'")

        ds = report.createDataSet()
        ds.setId(f"ds_{species_id}")
        ds.setLabel(species_id)
        ds.setDataReference(f"dg_{species_id}")

    return doc


def write_sedml(document: libsedml.SedDocument, path: str) -> str:
    if not libsedml.writeSedMLToFile(document, path):
        raise ExperimentBuildError(f"libsedml failed to write SED-ML to '{path}'")
    return path


@dataclass
class UniformTimeCourseSpec:
    """The parts of a SED-ML uniform-time-course document a simulation
    adapter needs to drive its own engine, extracted independent of any
    engine-specific importer. Adapters that don't have a reliable native
    COMBINE/SED-ML importer (Architecture, Layer 4) read this instead of
    re-implementing SED-ML parsing themselves.
    """

    model_source: str
    kisao_id: str
    initial_time: float
    output_start_time: float
    output_end_time: float
    number_of_steps: int
    reported_species_ids: list[str]


def read_uniform_time_course_spec(sedml_path: str) -> UniformTimeCourseSpec:
    document = libsedml.readSedMLFromFile(sedml_path)
    errors = [
        document.getError(i).getMessage()
        for i in range(document.getNumErrors())
        if document.getError(i).getSeverity() >= libsedml.LIBSEDML_SEV_ERROR
    ]
    if errors:
        raise ExperimentBuildError("SED-ML parsing failed: " + "; ".join(errors))

    simulation = document.getSimulation(0)
    sbml_model = document.getModel(0)
    algorithm = simulation.getAlgorithm()

    species_ids = []
    for i in range(document.getNumDataGenerators()):
        variable = document.getDataGenerator(i).getVariable(0)
        if variable.isSetSymbol() and variable.getSymbol() == _TIME_SYMBOL:
            continue
        match = _SPECIES_TARGET_RE.search(variable.getTarget())
        if match:
            species_ids.append(match.group(1))

    return UniformTimeCourseSpec(
        model_source=sbml_model.getSource(),
        kisao_id=algorithm.getKisaoID(),
        initial_time=simulation.getInitialTime(),
        output_start_time=simulation.getOutputStartTime(),
        output_end_time=simulation.getOutputEndTime(),
        number_of_steps=simulation.getNumberOfSteps(),
        reported_species_ids=species_ids,
    )
