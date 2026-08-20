"""Phase 11: ELN/LIMS-friendly export.

A COMBINE archive plus a curation record is already machine-reproducible
provenance (Phases 1-6). This module adds the missing human-facing piece:
one self-contained, timestamped Markdown document a researcher can paste
into (or attach to) a lab notebook / ELN entry, built entirely from the
same typed dataclasses the rest of Cradle already produces — no new data
shape invented for this, and no field here that isn't traceable back to a
real `EstimationReport`, `CurationRecord`, or `SimulationResult`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cradle.contracts.simulation_adapter import SimulationResult
from cradle.curation import CurationRecord
from cradle.estimation import EstimationReport


@dataclass
class LabReport:
    title: str
    model_curie: str
    combine_archive: str
    estimation: EstimationReport | None = None
    curation: CurationRecord | None = None
    comparison: dict[str, SimulationResult] = field(default_factory=dict)
    compared_species_id: str | None = None
    notes: list[str] = field(default_factory=list)
    generated_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _estimation_table(estimation: EstimationReport) -> str:
    lines = [
        "| parameter | fitted value | 95% CI | CV |",
        "|---|---|---|---|",
    ]
    for p in estimation.parameters:
        lines.append(
            f"| `{p.name}` | {p.fitted_value:.6g} "
            f"| [{p.lower_95ci:.6g}, {p.upper_95ci:.6g}] "
            f"| {p.coefficient_of_variation:.4g} |"
        )
    return "\n".join(lines)


def _comparison_table(comparison: dict[str, SimulationResult], species_id: str) -> str:
    lines = [
        f"| engine | final `{species_id}` value |",
        "|---|---|",
    ]
    for engine_name, result in comparison.items():
        final_value = result["trajectories"][species_id][-1]
        lines.append(f"| {engine_name} | {final_value:.6g} |")
    return "\n".join(lines)


def render_markdown(report: LabReport) -> str:
    sections = [
        f"# {report.title}",
        "",
        f"- **Model:** `{report.model_curie}`",
        f"- **Source archive:** `{report.combine_archive}`",
        f"- **Generated:** {report.generated_at_utc}",
        f"- **Curation tier:** {report.curation.tier if report.curation else 'non-curated (not evaluated)'}",
        "",
    ]

    if report.estimation is not None:
        sections += [
            "## Fitted parameters",
            "",
            f"Engine: `{report.estimation.engine}` "
            f"({report.estimation.optimization_method}), "
            f"{report.estimation.data_points} data points, "
            f"objective value {report.estimation.objective_value:.6g}.",
            "",
            "Confidence intervals are a Wald-type (Fisher-information) local "
            "approximation, not a full profile-likelihood scan — see "
            "`cradle.estimation.ParameterEstimate` for what that means for "
            "poorly-identified parameters.",
            "",
            _estimation_table(report.estimation),
            "",
        ]

    if report.comparison and report.compared_species_id:
        sections += [
            "## Cross-engine simulation comparison",
            "",
            _comparison_table(report.comparison, report.compared_species_id),
            "",
        ]

    if report.curation is not None:
        sections += [
            "## Curation evidence",
            "",
            *[f"- {check}" for check in report.curation.evidence],
            "",
            f"Reproduced independently on: {', '.join(report.curation.adapters_used)}.",
            "",
        ]

    if report.notes:
        sections += ["## Notes", "", *[f"- {note}" for note in report.notes], ""]

    return "\n".join(sections)


def write_lab_report(report: LabReport, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(render_markdown(report), encoding="utf-8")
    return path
