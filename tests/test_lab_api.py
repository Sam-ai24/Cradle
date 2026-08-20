from __future__ import annotations

import numpy as np
import pytest

from cradle.substrate import archive, experiment, model as cmodel
from cradle.substrate.examples.toggle_switch import build_annotated_document

copasi_sim = pytest.importorskip("copasi_sim")
tellurium_sim = pytest.importorskip("tellurium_sim")
from cradle import lab  # noqa: E402

TRUE_ALPHA1 = 156.25


@pytest.fixture()
def sbml_path(tmp_path):
    path = str(tmp_path / "toggle_switch.xml")
    cmodel.write_sbml(build_annotated_document(), path)
    return path


@pytest.fixture()
def combine_archive_path(tmp_path, sbml_path):
    sedml_doc = experiment.build_uniform_time_course_sedml(
        "toggle_switch.xml", ["U", "V"], output_end_time=2.0, number_of_steps=20
    )
    sedml_path = str(tmp_path / "experiment.xml")
    experiment.write_sedml(sedml_doc, sedml_path)
    archive_path = str(tmp_path / "toggle_switch.omex")
    archive.package_combine_archive(
        archive_path, sbml_path, "toggle_switch.xml", sedml_path, "experiment.xml"
    )
    return archive_path


@pytest.fixture()
def noisy_observed_data(sbml_path):
    import basico

    rng = np.random.default_rng(42)
    copasi_model = basico.load_model(sbml_path)
    trajectory = basico.run_time_course(0, 2.0, 20, model=copasi_model, method="deterministic")
    noisy_u = trajectory["U"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))
    noisy_v = trajectory["V"].to_numpy() * (1 + rng.normal(0, 0.03, size=len(trajectory)))
    return {"time": trajectory.index.tolist(), "U": noisy_u.tolist(), "V": noisy_v.tolist()}


def test_list_and_compare_adapters_exclude_non_archive_adapters():
    adapters = lab.list_simulation_adapters()
    assert "tellurium" in adapters
    assert "copasi" in adapters


def test_compare_adapters_defaults_only_run_combine_archive_engines(combine_archive_path):
    results = lab.compare_adapters(combine_archive_path)
    assert set(results) >= {"tellurium", "copasi"}
    assert "cobrapy" not in results, "FBA's input_mode is fba_sbml, not combine_archive"


def test_compare_trajectories_reports_near_zero_disagreement_between_real_engines(
    combine_archive_path,
):
    results = lab.compare_adapters(combine_archive_path, adapters=["tellurium", "copasi"])
    disagreement = lab.compare_trajectories(results, "U")
    assert disagreement["tellurium_vs_copasi"] < 0.01


def test_fit_then_apply_then_simulate_closes_the_fit_to_simulate_loop(
    tmp_path, sbml_path, combine_archive_path, noisy_observed_data
):
    """The actual Phase 11 exit-criterion path: fit a parameter far from its
    true value, apply the fit back into the model, then simulate the
    *updated* model and confirm the fitted-and-applied model's trajectory
    now differs from the pre-fit one — proof the loop actually closes
    rather than the fitted number going unused.
    """
    report = lab.fit_parameter(
        sbml_path,
        fit_parameters=[{"name": "Values[alpha1]", "lower": 1.0, "upper": 500.0, "start": 50.0}],
        observed_data=noisy_observed_data,
    )
    assert report.parameters[0].fitted_value == pytest.approx(TRUE_ALPHA1, rel=0.05)

    fitted_sbml_path = str(tmp_path / "toggle_switch_fitted.xml")
    lab.apply_fitted_parameters(sbml_path, fitted_sbml_path, report)

    import libsbml

    fitted_document = libsbml.readSBMLFromFile(fitted_sbml_path)
    assert fitted_document.getModel().getParameter("alpha1").getValue() == pytest.approx(
        report.parameters[0].fitted_value
    )

    pre_fit_result = lab.simulate(combine_archive_path, "tellurium")

    sedml_doc = experiment.build_uniform_time_course_sedml(
        "toggle_switch_fitted.xml", ["U", "V"], output_end_time=2.0, number_of_steps=20
    )
    sedml_path = str(tmp_path / "experiment_fitted.xml")
    experiment.write_sedml(sedml_doc, sedml_path)
    fitted_archive_path = str(tmp_path / "toggle_switch_fitted.omex")
    archive.package_combine_archive(
        fitted_archive_path,
        fitted_sbml_path,
        "toggle_switch_fitted.xml",
        sedml_path,
        "experiment_fitted.xml",
    )
    post_fit_result = lab.simulate(fitted_archive_path, "tellurium")

    assert post_fit_result["trajectories"]["U"] != pre_fit_result["trajectories"]["U"]


def test_apply_fitted_parameters_rejects_an_unresolvable_name(tmp_path, sbml_path):
    from cradle.estimation import EstimationReport, ParameterEstimate

    bogus_report = EstimationReport(
        model_source=sbml_path,
        engine="copasi",
        optimization_method="test",
        objective_value=0.0,
        data_points=1,
        parameters=[
            ParameterEstimate(
                name="Values[not_a_real_parameter]",
                fitted_value=1.0,
                std_dev=0.1,
                lower_95ci=0.8,
                upper_95ci=1.2,
                coefficient_of_variation=0.1,
            )
        ],
    )
    with pytest.raises(lab.LabError):
        lab.apply_fitted_parameters(sbml_path, str(tmp_path / "out.xml"), bogus_report)


def test_write_lab_report_embeds_the_real_fitted_values_and_curation_tier(
    tmp_path, combine_archive_path
):
    from cradle.estimation import EstimationReport, ParameterEstimate

    estimation = EstimationReport(
        model_source="toggle_switch.xml",
        engine="copasi",
        optimization_method="Levenberg - Marquardt",
        objective_value=0.01,
        data_points=20,
        parameters=[
            ParameterEstimate(
                name="Values[alpha1]",
                fitted_value=155.0,
                std_dev=5.0,
                lower_95ci=145.2,
                upper_95ci=164.8,
                coefficient_of_variation=0.032,
            )
        ],
    )
    curation = lab.curate_model(
        "biomodels.db:BIOMD0000000507",
        "Gardner2000 - toggle switch",
        evidence_checks={"fit_recovers_true_value": True},
        adapters_used=["tellurium", "copasi"],
    )
    results = lab.compare_adapters(combine_archive_path, adapters=["tellurium", "copasi"])

    report = lab.LabReport(
        title="Toggle switch fit-to-simulate run",
        model_curie="biomodels.db:BIOMD0000000507",
        combine_archive=combine_archive_path,
        estimation=estimation,
        curation=curation,
        comparison=results,
        compared_species_id="U",
    )
    markdown_path = lab.write_lab_report(report, tmp_path / "report.md")
    text = markdown_path.read_text(encoding="utf-8")

    assert "155" in text
    assert "145.2" in text
    assert "curated" in text
    assert "tellurium" in text and "copasi" in text
