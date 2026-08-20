"""Phase 11: the notebook-facing high-level API.

Everything here wraps an existing, already-verified Cradle capability
(the plugin registry, COPASI parameter estimation, curation, SED-ML/SBML
handling) behind function names and signatures meant to be called from a
notebook without reading `src/cradle/` first — the actual point of this
module, per the Phase 11 exit criterion. It adds no new science; it's a
front door onto Phases 1-9's real implementations.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

import libsbml

from cradle.contracts.simulation_adapter import SimulationResult
from cradle.curation import CurationRecord, promote_to_curated
from cradle.estimation import EstimationReport
from cradle.registry import discover
from cradle.substrate.archive import extract_combine_archive
from cradle.substrate.experiment import read_uniform_time_course_spec

#: basico's display-name convention for a global-parameter reference,
#: e.g. "Values[alpha1]" — the form `fit_parameters` entries use. What
#: `estimate_parameters()` actually echoes back on each `ParameterEstimate`
#: is COPASI's own longer form, "Values[alpha1].InitialValue" (confirmed by
#: `apply_fitted_parameters` actually running against a real fit, not
#: assumed from `fit_parameters`' input shape) — the optional `.Suffix` is
#: stripped along with the `Values[...]` wrapper.
_COPASI_GLOBAL_QUANTITY_RE = re.compile(r"^Values\[(.+?)\](?:\..+)?$")


class LabError(RuntimeError):
    pass


def list_simulation_adapters() -> list[str]:
    """Names of every currently-registered SimulationAdapter plugin."""
    return [plugin.entry_point_name for plugin in discover("simulation_adapter")]


def simulate(combine_archive: str, adapter: str = "tellurium") -> SimulationResult:
    """Run `combine_archive` on the registered adapter named `adapter`."""
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == adapter:
            return plugin.instance.run({"combine_archive": combine_archive}, {})
    raise LabError(
        f"no registered simulation adapter named {adapter!r}; "
        f"available: {list_simulation_adapters()}"
    )


def compare_adapters(
    combine_archive: str, adapters: list[str] | None = None
) -> dict[str, SimulationResult]:
    """Run `combine_archive` on several archive-driven adapters at once.

    Defaults to every registered adapter that declares
    `input_mode == "combine_archive"` — this deliberately excludes adapters
    like COBRApy's FBA wrapper (`input_mode == "fba_sbml"`), which can't
    run a kinetic time-course archive at all, rather than letting a mixed
    default silently fail on the wrong adapter.
    """
    if adapters is None:
        adapters = [
            plugin.entry_point_name
            for plugin in discover("simulation_adapter")
            if getattr(plugin.instance, "input_mode", None) == "combine_archive"
        ]
    return {name: simulate(combine_archive, name) for name in adapters}


def compare_trajectories(
    results: dict[str, SimulationResult], species_id: str
) -> dict[str, float]:
    """Max relative disagreement between each pair of engines in `results`
    for `species_id`'s final value — the same cross-adapter-agreement check
    Phase 2/4 used to prove the swap boundary, exposed as a reusable call
    instead of one-off test code.
    """
    finals = {name: result["trajectories"][species_id][-1] for name, result in results.items()}
    names = list(finals)
    disagreements: dict[str, float] = {}
    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            a, b = finals[name_a], finals[name_b]
            denom = max(abs(a), abs(b), 1e-12)
            disagreements[f"{name_a}_vs_{name_b}"] = abs(a - b) / denom
    return disagreements


def fit_parameter(
    sbml_path: str,
    fit_parameters: list[dict[str, Any]],
    observed_data: dict[str, list[float]],
    method: str = "Levenberg - Marquardt",
) -> EstimationReport:
    """Fit one or more global parameters against `observed_data` and report
    each with its Wald-approximation 95% confidence interval (Phase 6).

    Requires the `copasi_sim` plugin (`pip install -e plugins/copasi_sim`)
    — parameter estimation is a COPASI-specific capability, not part of
    the shared SimulationAdapter contract every engine implements.
    """
    try:
        from copasi_sim.estimation import estimate_parameters
    except ImportError as exc:
        raise LabError(
            "fit_parameter() requires the copasi_sim plugin: "
            "pip install -e plugins/copasi_sim"
        ) from exc
    return estimate_parameters(sbml_path, fit_parameters, observed_data, method=method)


def apply_fitted_parameters(
    sbml_in: str, sbml_out: str, estimation_report: EstimationReport
) -> str:
    """Write a copy of `sbml_in` with every fitted parameter's value updated
    to `estimation_report`'s fitted value — the step that actually closes
    the "fit-to-simulate" loop instead of leaving the fit as a number no
    subsequent simulation ever uses.

    COPASI's fit-parameter names are its own quantity-reference syntax
    (`"Values[alpha1]"`), not necessarily the bare SBML id — this strips
    that wrapper before looking the parameter up, and fails loudly (rather
    than silently skipping) if a fitted name doesn't resolve to a real
    global parameter in `sbml_in`.
    """
    document = libsbml.readSBMLFromFile(sbml_in)
    model = document.getModel()

    for estimate in estimation_report.parameters:
        match = _COPASI_GLOBAL_QUANTITY_RE.match(estimate.name)
        parameter_id = match.group(1) if match else estimate.name
        parameter = model.getParameter(parameter_id)
        if parameter is None:
            raise LabError(
                f"fitted parameter '{estimate.name}' (parsed as id '{parameter_id}') "
                f"has no matching global parameter in '{sbml_in}'"
            )
        parameter.setValue(estimate.fitted_value)

    if not libsbml.writeSBMLToFile(document, sbml_out):
        raise LabError(f"libsbml failed to write updated SBML to '{sbml_out}'")
    return sbml_out


def curate_model(
    model_curie: str,
    title: str,
    evidence_checks: dict[str, bool],
    adapters_used: list[str],
) -> CurationRecord:
    """Thin pass-through to `cradle.curation.promote_to_curated` — kept here
    so a notebook workflow can stay entirely within `cradle.lab` for the
    fit -> validate -> simulate -> curate pipeline (Phase 11's exit
    criterion) without reaching into `cradle.curation` directly.
    """
    return promote_to_curated(model_curie, title, evidence_checks, adapters_used)


def read_sedml_summary(combine_archive: str) -> dict[str, Any]:
    """The SED-ML experiment's key facts (algorithm, duration, reported
    species) for `combine_archive`, extracted without running anything —
    useful for a report/notebook that wants to state what a run *asked
    for* before showing what it produced.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        sedml_path = extract_combine_archive(combine_archive, tmp_dir)
        spec = read_uniform_time_course_spec(sedml_path)
    return {
        "model_source": spec.model_source,
        "kisao_id": spec.kisao_id,
        "output_end_time": spec.output_end_time,
        "number_of_steps": spec.number_of_steps,
        "reported_species_ids": spec.reported_species_ids,
    }


def plot_comparison(results: dict[str, SimulationResult], species_id: str, ax=None):
    """Overlay `species_id`'s trajectory from every engine in `results` on
    one matplotlib axes — the one plotting helper `cradle.lab` provides,
    since a lab collaborator comparing two runs shouldn't have to know
    `SimulationResult`'s dict shape to see them plotted together.
    """
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots()
    for engine_name, result in results.items():
        ax.plot(result["t"], result["trajectories"][species_id], label=f"{engine_name}")
    ax.set_xlabel("time")
    ax.set_ylabel(species_id)
    ax.set_title(f"{species_id} across {len(results)} engine(s)")
    ax.legend()
    return ax
