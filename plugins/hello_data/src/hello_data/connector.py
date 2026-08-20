from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord


class HelloDataConnector:
    """Trivial reference implementation of `cradle.contracts.DataConnector`.

    Returns a hard-coded record instead of calling a real API. It exists
    only to prove the entry_points registration and conformance mechanism
    work end to end, per Roadmap Phase 0. Phase 3 replaces this with real
    connectors (UniProt, PDB, Reactome, BioModels, ...).
    """

    name = "hello-data"

    def fetch(self, curie: str) -> ConnectorRecord:
        return {
            "curie": curie,
            "source": "hello-data (stub)",
            "license": "CC0-1.0",
            "data": {"note": "placeholder record, no real lookup performed"},
        }
