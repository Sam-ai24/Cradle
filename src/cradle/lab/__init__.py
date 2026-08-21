"""Phase 11: the lab-facing notebook API.

`cradle.lab.api` is the core (no extra dependencies beyond core Cradle);
`cradle.lab.report` builds ELN-friendly Markdown reports; `cradle.lab.widgets`
needs the optional `lab` extra and is not imported here, so importing
`cradle.lab` itself never requires ipywidgets to be installed.
"""

from __future__ import annotations

from cradle.lab.api import (
    LabError,
    apply_fitted_parameters,
    compare_adapters,
    compare_trajectories,
    curate_model,
    fit_parameter,
    list_simulation_adapters,
    plot_comparison,
    read_sedml_summary,
    simulate,
)
from cradle.lab.bridges import BridgeStatus, check_bridge, check_chimerax, check_namd
from cradle.lab.report import LabReport, render_markdown, write_lab_report

__all__ = [
    "BridgeStatus",
    "LabError",
    "LabReport",
    "apply_fitted_parameters",
    "check_bridge",
    "check_chimerax",
    "check_namd",
    "compare_adapters",
    "compare_trajectories",
    "curate_model",
    "fit_parameter",
    "list_simulation_adapters",
    "plot_comparison",
    "read_sedml_summary",
    "render_markdown",
    "simulate",
    "write_lab_report",
]
