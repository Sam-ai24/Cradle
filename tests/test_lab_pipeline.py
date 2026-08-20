from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("snakemake")
pytest.importorskip("copasi_sim")
pytest.importorskip("tellurium_sim")

REPO_ROOT = Path(__file__).resolve().parent.parent
TRUE_ALPHA1 = 156.25


def test_snakemake_lab_pipeline_runs_end_to_end_and_agrees_within_tolerance(tmp_path):
    """Phase 11's actual exit-criterion pipeline (fit -> apply -> simulate
    on two adapters -> benchmark), run as a real subprocess against
    workflows/Snakefile — not a mock of what the pipeline would do, the
    same command a researcher would type. Confirmed to be the actually-
    runnable executor on this platform after cwltool's own Windows
    incompatibilities ruled it out for the equivalent workflows/lab_pipeline.cwl
    (see docs/ROADMAP.md, Phase 11).
    """
    output_dir = tmp_path / "pipeline_output"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "snakemake",
            "-s",
            str(REPO_ROOT / "workflows" / "Snakefile"),
            "--cores",
            "1",
            "--config",
            f"output_dir={output_dir.as_posix()}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    estimation = json.loads((output_dir / "estimation_report.json").read_text(encoding="utf-8"))
    assert estimation["parameters"][0]["fitted_value"] == pytest.approx(TRUE_ALPHA1, rel=0.05)

    benchmark = json.loads((output_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert benchmark["within_tolerance"] is True
    assert benchmark["disagreements"]["tellurium_vs_copasi"] < 0.01
