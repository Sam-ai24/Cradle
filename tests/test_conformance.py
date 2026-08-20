from __future__ import annotations

import pytest

from cradle.conformance.checks import CHECKS
from cradle.contracts.errors import NotConfiguredError
from cradle.registry import discover_all


@pytest.mark.parametrize(
    "kind", ["data_connector", "simulation_adapter", "ai_model_adapter"]
)
def test_at_least_one_plugin_registered(kind: str) -> None:
    discovered = discover_all()
    assert discovered[kind], f"no plugins registered for {kind}"


def test_all_registered_plugins_pass_conformance() -> None:
    discovered = discover_all()
    failures = []
    skipped = []
    for kind, plugins in discovered.items():
        for plugin in plugins:
            try:
                CHECKS[kind](plugin.instance)
            except NotConfiguredError as exc:
                skipped.append(f"{kind}:{plugin.entry_point_name} - {exc}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{kind}:{plugin.entry_point_name} - {exc}")
    assert not failures, "\n".join(failures)
    if skipped:
        pytest.skip("; ".join(skipped))  # only reached if there were no failures
