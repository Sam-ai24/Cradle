"""Phase 11: the interactive Jupyter widget.

Requires the optional `lab` extra (`pip install -e ".[lab]"`) for
`ipywidgets` — exactly the same graceful-degradation shape the AI
orchestration layer (Phase 5) uses for API keys: every other Cradle
capability, including every other function in `cradle.lab`, works with
zero widget dependencies installed, and importing this specific module
without them raises one clear, actionable error instead of an import
traceback from deep inside `ipywidgets`.
"""

from __future__ import annotations

from typing import Any

from cradle.lab.api import LabError, list_simulation_adapters, plot_comparison, simulate


def _require_ipywidgets():
    try:
        import ipywidgets  # noqa: F401
    except ImportError as exc:
        raise LabError(
            "the interactive explorer widget requires the 'lab' extra: "
            'pip install -e ".[lab]"'
        ) from exc


def explorer(combine_archive: str, species_id: str, adapters: list[str] | None = None) -> Any:
    """An ipywidgets dropdown + "Run" button + live matplotlib plot for
    exploring one COMBINE archive across registered simulation adapters,
    without the researcher writing any `cradle.registry`/adapter-lookup
    code themselves. Returns the composed widget; call `display()` on it
    in a notebook cell (or just leave it as the cell's last expression).
    """
    _require_ipywidgets()
    import ipywidgets as widgets
    from IPython.display import clear_output

    adapters = adapters or list_simulation_adapters()
    dropdown = widgets.Dropdown(options=adapters, description="adapter:")
    run_button = widgets.Button(description="Run", button_style="primary")
    output = widgets.Output()

    def _on_click(_button):
        with output:
            clear_output(wait=True)
            result = simulate(combine_archive, dropdown.value)
            plot_comparison({dropdown.value: result}, species_id)

    run_button.on_click(_on_click)
    return widgets.VBox([widgets.HBox([dropdown, run_button]), output])
