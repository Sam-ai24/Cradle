from __future__ import annotations

from typing import Any

from cradle.contracts.errors import NotConfiguredError
from cradle.registry import discover


def available_orchestrators() -> list[Any]:
    """Every registered AI adapter implementing the "orchestration"
    contract (Architecture, Layer 5) — regardless of whether any of them
    currently has an API key configured.
    """
    return [
        plugin.instance
        for plugin in discover("ai_model_adapter")
        if getattr(plugin.instance, "contract_type", None) == "orchestration"
    ]


def get_orchestrator(prefer: str | None = None) -> Any:
    """Return the first configured orchestration adapter, optionally
    preferring one by name (e.g. `prefer="claude"`).

    AI orchestration is entirely optional — every other Cradle capability
    (simulation, data connectors, curation) works with zero AI adapters
    configured. This is the single place that decision surfaces: if no
    provider has a key set, this raises `NotConfiguredError` listing every
    available option and exactly which environment variable enables each,
    rather than a researcher discovering a missing key as a stack trace
    three layers down inside whichever adapter they happened to try first.
    """
    orchestrators = available_orchestrators()
    if not orchestrators:
        raise NotConfiguredError(
            "No AI orchestration adapter is installed. This feature is optional — "
            "install one (e.g. `pip install -e plugins/llm_orchestrator`) if you want it."
        )

    if prefer:
        orchestrators = sorted(orchestrators, key=lambda o: o.name != prefer)

    for adapter in orchestrators:
        if adapter.is_configured:
            return adapter

    options = ", ".join(f"{o.api_key_env_var} (for '{o.name}')" for o in orchestrators)
    raise NotConfiguredError(
        "AI orchestration is optional and currently off: no provider has an API key "
        f"configured. Set one of: {options}. Every other Cradle capability (simulation, "
        "data connectors, curation) works fully without this."
    )
