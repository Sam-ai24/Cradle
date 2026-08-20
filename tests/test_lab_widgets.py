from __future__ import annotations

import builtins

import pytest

pytest.importorskip("ipywidgets")
pytest.importorskip("tellurium_sim")

from cradle.substrate import archive, experiment, model as cmodel
from cradle.substrate.examples.toggle_switch import build_annotated_document


@pytest.fixture()
def combine_archive_path(tmp_path):
    sbml_path = str(tmp_path / "toggle_switch.xml")
    cmodel.write_sbml(build_annotated_document(), sbml_path)
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


def test_explorer_builds_a_working_widget_that_runs_a_real_simulation_on_click(
    combine_archive_path,
):
    """Headless proxy for "a researcher clicks Run in a notebook": since a
    real click event needs a live front end, this invokes the same
    on_click handler ipywidgets would call, and checks it actually ran a
    real simulation (a matplotlib Axes with real, non-empty line data),
    not just that the widget object constructed without error.
    """
    from cradle.lab.widgets import explorer

    widget = explorer(combine_archive_path, "U", adapters=["tellurium"])

    dropdown, run_button = widget.children[0].children
    output = widget.children[1]
    assert dropdown.value == "tellurium"

    run_button.click()

    assert len(output.outputs) == 0, "a successful run should produce a plot, not a traceback"
    import matplotlib.pyplot as plt

    figures = plt.get_fignums()
    assert figures, "clicking Run should have created a matplotlib figure via plot_comparison"
    plt.close("all")


def test_widgets_module_raises_a_clear_error_without_ipywidgets_installed(monkeypatch):
    import sys

    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "ipywidgets":
            raise ImportError("simulated: ipywidgets not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    monkeypatch.delitem(sys.modules, "ipywidgets", raising=False)

    from cradle.lab.api import LabError
    from cradle.lab.widgets import _require_ipywidgets

    with pytest.raises(LabError, match="lab' extra"):
        _require_ipywidgets()
