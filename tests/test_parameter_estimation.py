from __future__ import annotations

import numpy as np
import pytest

from cradle.substrate import model as cmodel
from cradle.substrate.examples.toggle_switch import build_annotated_document

copasi_sim = pytest.importorskip("copasi_sim")
from copasi_sim.estimation import estimate_parameters  # noqa: E402

TRUE_ALPHA1 = 156.25


@pytest.fixture()
def sbml_path(tmp_path):
    path = str(tmp_path / "toggle_switch.xml")
    cmodel.write_sbml(build_annotated_document(), path)
    return path


@pytest.fixture()
def noisy_observed_data(sbml_path):
    """Synthetic data generated at the real, known alpha1 (156.25, the
    Gardner et al. 2000 fitted value Phase 1 already uses) plus 3%
    multiplicative noise — a fit against this has a ground truth to check
    the reported uncertainty against, which a fit against real experimental
    data never would.
    """
    import basico

    rng = np.random.default_rng(42)
    model = basico.load_model(sbml_path)
    trajectory = basico.run_time_course(0, 2.0, 20, model=model, method="deterministic")

    noisy_u = trajectory["U"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))
    noisy_v = trajectory["V"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))
    return {
        "time": trajectory.index.tolist(),
        "U": noisy_u.tolist(),
        "V": noisy_v.tolist(),
    }


def test_fitted_parameter_reports_a_confidence_interval_containing_the_true_value(
    sbml_path, noisy_observed_data
):
    """The actual point of Phase 6: not just that a number comes back, but
    that the reported uncertainty means what it claims to. Deliberately
    starts the optimizer far from the true value (50 vs. the true 156.25)
    so this can't pass by accident of a lucky default.
    """
    report = estimate_parameters(
        sbml_path,
        fit_parameters=[
            {"name": "Values[alpha1]", "lower": 1.0, "upper": 500.0, "start": 50.0}
        ],
        observed_data=noisy_observed_data,
    )

    assert report.data_points > 0
    assert len(report.parameters) == 1

    estimate = report.parameters[0]
    assert estimate.fitted_value == pytest.approx(TRUE_ALPHA1, rel=0.05)
    assert estimate.std_dev > 0, "a real fit must report nonzero uncertainty, not a bare point value"
    assert estimate.lower_95ci < TRUE_ALPHA1 < estimate.upper_95ci, (
        f"true value {TRUE_ALPHA1} falls outside the reported 95% CI "
        f"[{estimate.lower_95ci}, {estimate.upper_95ci}] — the uncertainty is wrong, "
        f"not just imprecise"
    )
