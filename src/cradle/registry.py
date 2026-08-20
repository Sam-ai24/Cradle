from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

#: Cradle's three plugin kinds and the entry_points group each registers under.
#: A plugin becomes visible to Cradle by declaring one of these groups in its
#: own package's [project.entry-points] table — no code change to Cradle
#: itself is required to add, remove, or replace a plugin.
GROUPS: dict[str, str] = {
    "data_connector": "cradle.data_connectors",
    "simulation_adapter": "cradle.simulation_adapters",
    "ai_model_adapter": "cradle.ai_model_adapters",
}


@dataclass
class DiscoveredPlugin:
    kind: str
    entry_point_name: str
    distribution: str | None
    instance: Any


def discover(kind: str) -> list[DiscoveredPlugin]:
    """Load every plugin registered under Cradle's entry_points group for `kind`.

    Each entry point must resolve to a zero-argument callable (a class or
    factory function) that returns an instance satisfying the matching
    Protocol in `cradle.contracts`.
    """
    group = GROUPS[kind]
    plugins = []
    for ep in entry_points(group=group):
        factory = ep.load()
        instance = factory()
        plugins.append(
            DiscoveredPlugin(
                kind=kind,
                entry_point_name=ep.name,
                distribution=ep.dist.name if ep.dist else None,
                instance=instance,
            )
        )
    return plugins


def discover_all() -> dict[str, list[DiscoveredPlugin]]:
    return {kind: discover(kind) for kind in GROUPS}
