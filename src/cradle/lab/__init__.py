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
from cradle.lab.essentiality import (
    IML1515_CURIE,
    IML1515_URL,
    KNOWN,
    auroc,
    binary_metrics,
    classify_fba_growth,
    compare_essentiality,
    confusion_counts,
    download_iml1515,
    fba_gene_table,
    fba_knockout,
    fba_single_gene_deletion,
    fetch_pec_essentiality,
    fetch_string_degrees,
    fetch_uniprot_essentiality,
    plot_essentiality,
    run_ecoli_essentiality_flagship,
    write_essentiality_report,
)
from cradle.lab.report import LabReport, render_markdown, write_lab_report

__all__ = [
    "BridgeStatus",
    "IML1515_CURIE",
    "IML1515_URL",
    "KNOWN",
    "LabError",
    "LabReport",
    "apply_fitted_parameters",
    "auroc",
    "binary_metrics",
    "check_bridge",
    "check_chimerax",
    "check_namd",
    "classify_fba_growth",
    "compare_adapters",
    "compare_essentiality",
    "compare_trajectories",
    "confusion_counts",
    "curate_model",
    "download_iml1515",
    "fba_gene_table",
    "fba_knockout",
    "fba_single_gene_deletion",
    "fetch_pec_essentiality",
    "fetch_string_degrees",
    "fetch_uniprot_essentiality",
    "fit_parameter",
    "list_simulation_adapters",
    "plot_comparison",
    "plot_essentiality",
    "read_sedml_summary",
    "render_markdown",
    "run_ecoli_essentiality_flagship",
    "simulate",
    "write_essentiality_report",
    "write_lab_report",
]
