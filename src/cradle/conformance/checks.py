from __future__ import annotations

import tempfile
from typing import Any, Callable

from cradle.contracts.ai_model_adapter import AIModelAdapter
from cradle.contracts.data_connector import DataConnector
from cradle.contracts.simulation_adapter import SimulationAdapter


class ConformanceError(AssertionError):
    """Raised when a registered plugin does not satisfy its contract."""


def _assert_valid_record(instance: Any, record: Any) -> None:
    for key in ("curie", "source", "license", "data"):
        if key not in record:
            raise ConformanceError(f"{instance.name} fetch() result missing '{key}'")


def check_data_connector(instance: Any) -> None:
    if not isinstance(instance, DataConnector):
        raise ConformanceError(f"{instance!r} does not implement DataConnector")

    from cradle.knowledge.gate import LicenseGate, LicenseNotAcknowledgedError

    if isinstance(instance, LicenseGate):
        # A gated connector's correct behavior is to refuse until
        # acknowledged — verify the refusal actually happens, then verify
        # it actually works once acknowledged, rather than either treating
        # the refusal as a failure or skipping the gate untested.
        probe_curie = getattr(instance, "conformance_curie", "test:0000")
        try:
            instance.fetch(probe_curie)
        except LicenseNotAcknowledgedError:
            pass
        else:
            raise ConformanceError(
                f"{instance.name} is license-gated but fetch() succeeded without acknowledgment"
            )
        instance.acknowledge()
        _assert_valid_record(instance, instance.fetch(probe_curie))
        return

    # Real connectors declare a known-good CURIE to smoke-test against
    # (they can't answer the Phase 0 toy "test:0000"); hello_data has none
    # and keeps using that literal, unmodified.
    probe_curie = getattr(instance, "conformance_curie", "test:0000")
    _assert_valid_record(instance, instance.fetch(probe_curie))


def _check_toy_simulation_adapter(instance: Any) -> None:
    """Conformance check for Phase 0-style adapters that take a plain
    parameter dict rather than a real COMBINE archive (`input_mode` unset
    or "toy_dict") — e.g. the `hello_sim` reference plugin.
    """
    model = {"k": 0.5, "x0": 10.0}
    config = {"t_end": 1.0, "steps": 5}
    result = instance.run(model, config)
    for key in ("t", "trajectories", "engine"):
        if key not in result:
            raise ConformanceError(f"{instance.name} run() result missing '{key}'")
    if len(result["t"]) != config["steps"] + 1:
        raise ConformanceError(
            f"{instance.name} run() returned {len(result['t'])} timepoints, "
            f"expected {config['steps'] + 1}"
        )


def _check_combine_archive_simulation_adapter(instance: Any) -> None:
    """Conformance check for real adapters (`input_mode = "combine_archive"`)
    that execute the SED-ML task described inside a COMBINE archive —
    the BioSimulators-style contract (Architecture, Layer 4). Runs the same
    reference archive Phase 1 already validated, rather than a toy input
    these adapters were never meant to understand.
    """
    # Imported lazily: pulls in the substrate module only when an adapter
    # actually declares this mode, keeping the toy path dependency-free.
    from cradle.conformance.fixtures import (
        REFERENCE_NUMBER_OF_STEPS,
        REFERENCE_SPECIES_IDS,
        build_reference_combine_archive,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = build_reference_combine_archive(tmp_dir)
        result = instance.run({"combine_archive": archive_path}, {})

    for key in ("t", "trajectories", "engine"):
        if key not in result:
            raise ConformanceError(f"{instance.name} run() result missing '{key}'")
    if len(result["t"]) != REFERENCE_NUMBER_OF_STEPS + 1:
        raise ConformanceError(
            f"{instance.name} run() returned {len(result['t'])} timepoints, "
            f"expected {REFERENCE_NUMBER_OF_STEPS + 1}"
        )
    for species_id in REFERENCE_SPECIES_IDS:
        if species_id not in result["trajectories"]:
            raise ConformanceError(
                f"{instance.name} run() trajectories missing '{species_id}'"
            )


def _check_fba_sbml_simulation_adapter(instance: Any) -> None:
    """Conformance check for constraint-based/FBA adapters
    (`input_mode = "fba_sbml"`) that take a direct SBML-fbc model rather
    than a time-course COMBINE archive — a steady-state analysis has no
    time axis to describe via SED-ML's uniform-time-course type.
    """
    from cradle.conformance.fixtures import build_reference_fba_sbml

    with tempfile.TemporaryDirectory() as tmp_dir:
        sbml_path = build_reference_fba_sbml(tmp_dir)
        result = instance.run({"sbml_path": sbml_path}, {})

    for key in ("t", "trajectories", "engine"):
        if key not in result:
            raise ConformanceError(f"{instance.name} run() result missing '{key}'")
    if not result["trajectories"]:
        raise ConformanceError(f"{instance.name} run() returned no flux values")


def check_simulation_adapter(instance: Any) -> None:
    if not isinstance(instance, SimulationAdapter):
        raise ConformanceError(f"{instance!r} does not implement SimulationAdapter")

    input_mode = getattr(instance, "input_mode", "toy_dict")
    if input_mode == "combine_archive":
        _check_combine_archive_simulation_adapter(instance)
    elif input_mode == "fba_sbml":
        _check_fba_sbml_simulation_adapter(instance)
    else:
        _check_toy_simulation_adapter(instance)


def check_ai_model_adapter(instance: Any) -> None:
    if not isinstance(instance, AIModelAdapter):
        raise ConformanceError(f"{instance!r} does not implement AIModelAdapter")
    prediction = instance.predict({"probe": True})
    for key in ("output", "provenance"):
        if key not in prediction:
            raise ConformanceError(f"{instance.name} predict() result missing '{key}'")


CHECKS: dict[str, Callable[[Any], None]] = {
    "data_connector": check_data_connector,
    "simulation_adapter": check_simulation_adapter,
    "ai_model_adapter": check_ai_model_adapter,
}
