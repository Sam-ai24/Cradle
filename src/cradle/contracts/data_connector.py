from __future__ import annotations

from typing import Any, Protocol, TypedDict, runtime_checkable


class ConnectorRecord(TypedDict):
    curie: str
    source: str
    license: str
    data: dict[str, Any]


@runtime_checkable
class DataConnector(Protocol):
    """Contract for a pluggable knowledge-source connector (Architecture, Layer 6).

    Every record a connector returns is addressed by a CURIE (resolved through
    identifiers.org / MIRIAM) and declares its source and license, so a
    restricted source can be license-gated by the registry without any
    calling code knowing which connector produced the record.
    """

    name: str

    def fetch(self, curie: str) -> ConnectorRecord: ...
