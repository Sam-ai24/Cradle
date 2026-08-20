from __future__ import annotations

from typing import Any

from cradle.registry import discover


def resolve_all(curie: str) -> dict[str, dict[str, Any]]:
    """Fan a single CURIE out across every registered data connector that
    accepts it, keyed by entry-point name. A connector's `accepts()` is
    optional (defaults to "always accepts", preserving Phase 0's
    `hello_data` behavior) — this is how one query reaches whichever
    combination of sources happens to be installed, without the caller
    naming any of them (Architecture, Layer 6). One source erroring
    (network failure, license not acknowledged, unknown identifier)
    doesn't fail the whole query; it's reported alongside the sources that
    did answer.
    """
    results: dict[str, dict[str, Any]] = {}
    for plugin in discover("data_connector"):
        instance = plugin.instance
        accepts = getattr(instance, "accepts", None)
        if accepts is not None and not accepts(curie):
            continue
        try:
            record = instance.fetch(curie)
        except Exception as exc:  # noqa: BLE001 - isolate one source's failure from the rest
            results[plugin.entry_point_name] = {"error": str(exc)}
        else:
            results[plugin.entry_point_name] = dict(record)
    return results
