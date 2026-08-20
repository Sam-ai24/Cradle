from __future__ import annotations

import os
from typing import Any

from cradle.contracts.data_connector import ConnectorRecord


class LicenseNotAcknowledgedError(PermissionError):
    pass


def _acknowledged_via_env(name: str) -> bool:
    env_var = f"CRADLE_LICENSE_ACK_{name.upper().replace('-', '_')}"
    return os.environ.get(env_var) == "1"


class LicenseGate:
    """Wraps a restricted-license DataConnector so it's off by default and
    only usable once a deployment explicitly acknowledges the source's
    terms (Architecture, Layer 6: license traps like KEGG "become optional
    adapters... toggled per-deployment... never a hard dependency").

    Implements the DataConnector protocol itself (delegates `name`/`fetch`/
    `accepts`), so a gated connector registers and is discovered exactly
    like an open one — the gate is enforced at call time, not by hiding
    the connector from the plugin registry.
    """

    def __init__(self, connector: Any, license_summary: str) -> None:
        self._connector = connector
        self.license_summary = license_summary
        self._acknowledged = _acknowledged_via_env(connector.name)

    @property
    def name(self) -> str:
        return self._connector.name

    @property
    def conformance_curie(self) -> str:
        return getattr(self._connector, "conformance_curie", "test:0000")

    def acknowledge(self) -> None:
        self._acknowledged = True

    def fetch(self, curie: str) -> ConnectorRecord:
        if not self._acknowledged:
            raise LicenseNotAcknowledgedError(
                f"'{self._connector.name}' is license-gated ({self.license_summary}). "
                f"Call .acknowledge() or set CRADLE_LICENSE_ACK_"
                f"{self._connector.name.upper()}=1 before fetching."
            )
        return self._connector.fetch(curie)

    def accepts(self, curie: str) -> bool:
        accepts = getattr(self._connector, "accepts", None)
        return accepts(curie) if accepts is not None else True
