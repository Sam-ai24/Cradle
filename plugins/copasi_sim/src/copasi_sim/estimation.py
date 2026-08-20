from __future__ import annotations

import tempfile
from typing import Any

import basico
import pandas as pd

from cradle.estimation import EstimationReport, ParameterEstimate

#: 95% under the Wald/normal approximation this method uses (see
#: cradle.estimation.ParameterEstimate's docstring on that limitation).
_Z_95 = 1.96


class EstimationError(RuntimeError):
    pass


def estimate_parameters(
    sbml_path: str,
    fit_parameters: list[dict[str, Any]],
    observed_data: dict[str, list[float]],
    method: str = "Levenberg - Marquardt",
) -> EstimationReport:
    """Fit `fit_parameters` (each `{"name", "lower", "upper", "start"}`,
    where `name` is a global-parameter display name — see
    `basico.get_parameters()`) against `observed_data` (a dict with a
    "time" key plus one list per observed species, matching
    `cradle.substrate.experiment`'s species-id convention) and report
    each fitted value with its Wald-approximation uncertainty.

    This is COPASI-specific functionality beyond the shared
    SimulationAdapter contract's `run()` — parameter estimation with
    identifiability statistics is a real capability gap between engines
    (Architecture Layer 4 already calls this out as a COPASI-specific
    strength), not something every adapter is expected to implement.
    """
    times = observed_data["time"]
    species_columns = {
        f"[{species_id}]": values
        for species_id, values in observed_data.items()
        if species_id != "time"
    }
    experiment_df = pd.DataFrame({"Time": times, **species_columns})

    copasi_model = basico.load_model(sbml_path)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # basico.add_experiment writes the data to disk as a side effect
        # (COPASI's fitting task reads it back from a file); without an
        # explicit data_dir it defaults to the current working directory,
        # which would litter whatever directory happens to be cwd when
        # this runs — a real bug, not just untidy.
        basico.add_experiment("cradle_fit", experiment_df, model=copasi_model, data_dir=tmp_dir)
        basico.set_fit_parameters(fit_parameters, model=copasi_model)
        basico.run_parameter_estimation(method=method, model=copasi_model)
        stats = basico.get_fit_statistic(include_parameters=True, model=copasi_model)

    if not stats["parameters"]:
        raise EstimationError(
            f"COPASI's parameter estimation produced no fitted parameters for '{sbml_path}' "
            f"— check that fit_parameters names match basico.get_parameters()'s display names"
        )

    estimates = []
    for entry in stats["parameters"]:
        value = entry["value"]
        std_dev = entry["std_dev"]
        estimates.append(
            ParameterEstimate(
                name=entry["name"],
                fitted_value=value,
                std_dev=std_dev,
                lower_95ci=value - _Z_95 * std_dev,
                upper_95ci=value + _Z_95 * std_dev,
                coefficient_of_variation=entry["coeff_of_variation"],
            )
        )

    return EstimationReport(
        model_source=sbml_path,
        engine="copasi",
        optimization_method=method,
        objective_value=stats["obj"],
        data_points=stats["valid_data_points"],
        parameters=estimates,
    )
