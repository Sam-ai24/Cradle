from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = "https://data.rcsb.org/rest/v1/core/entry/{entry_id}"


class RcsbPdbConnector:
    """Experimental protein structure (Architecture, Layer 6 MVP source;
    CC0, safe to cache and redistribute per docs/RESOURCES.md).
    """

    name = "pdb"
    #: 1TUP — TP53 DNA-binding domain complexed with DNA, a real deposited
    #: structure used to conformance-test against the live API.
    conformance_curie = "pdb:1TUP"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "pdb"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, entry_id = parse_curie(curie)
        payload = get_json(_API.format(entry_id=entry_id))
        methods = [m.get("method") for m in payload.get("exptl", [])]
        return {
            "curie": curie,
            "source": "RCSB PDB",
            "license": "CC0",
            "data": {
                "entry_id": entry_id,
                "title": payload.get("struct", {}).get("title"),
                "experimental_methods": methods,
                "resolution_angstrom": payload.get("rcsb_entry_info", {}).get(
                    "resolution_combined"
                ),
            },
        }
