from __future__ import annotations

from typing import Any

from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_RESOLVER_API = "https://resolver.api.identifiers.org/{curie}"


class ResolutionError(RuntimeError):
    pass


def resolve_curie(curie: str) -> list[dict[str, Any]]:
    """Dereference any CURIE via the identifiers.org/MIRIAM resolver,
    independent of which Cradle connector (if any) produced it — this is
    what lets a CURIE stamped on a model entity (Layer 1/8) or returned by
    a data connector (Layer 6) always be traced back to a canonical
    provider URL, even for namespaces Cradle has no connector for yet.
    """
    parse_curie(curie)  # raises InvalidCurieError on bad syntax before we hit the network
    payload = get_json(_RESOLVER_API.format(curie=curie))
    resolved = payload.get("payload", {}).get("resolvedResources")
    if not resolved:
        raise ResolutionError(f"identifiers.org has no registered provider for '{curie}'")
    return resolved
