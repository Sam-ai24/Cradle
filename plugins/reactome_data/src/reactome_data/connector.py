from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_ENTITY_API = "https://reactome.org/ContentService/data/query/enhanced/{stable_id}"
_MAPPING_API = "https://reactome.org/ContentService/data/mapping/UniProt/{accession}/reactions"


class ReactomeConnector:
    """Curated pathways/reactions (Architecture, Layer 6 MVP source; CC0,
    safe to cache and redistribute per docs/RESOURCES.md).

    Accepts two CURIE namespaces: its own (`reactome:R-HSA-...`, a direct
    entity lookup) and `uniprot:...` (via Reactome's cross-reference
    mapping endpoint, returning the reactions a given protein participates
    in) — the same protein-to-pathway query the Phase 3 exit criterion
    exercises across multiple sources at once.
    """

    name = "reactome"
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace in ("reactome", "uniprot")

    def fetch(self, curie: str) -> ConnectorRecord:
        namespace, local_id = parse_curie(curie)
        if namespace == "reactome":
            payload = get_json(_ENTITY_API.format(stable_id=local_id))
            data = {
                "stable_id": payload.get("stId"),
                "display_name": payload.get("displayName"),
                "species": payload.get("speciesName"),
            }
        else:
            reactions = get_json(_MAPPING_API.format(accession=local_id))
            data = {
                "queried_uniprot_accession": local_id,
                "reaction_count": len(reactions),
                "reactions": [
                    {"stable_id": r.get("stId"), "display_name": r.get("displayName")}
                    for r in reactions[:10]
                ],
            }
        return {"curie": curie, "source": "Reactome", "license": "CC0", "data": data}
