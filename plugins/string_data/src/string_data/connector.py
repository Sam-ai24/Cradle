from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_RESOLVE_API = "https://string-db.org/api/json/get_string_ids?identifiers={accession}&species={species}"
_NETWORK_API = "https://string-db.org/api/json/network?identifiers={string_id}&species={species}&limit=10"

#: STRING requires an NCBI taxon id per query; a bare UniProt accession
#: doesn't carry one. Defaulting to human is a known MVP limitation, not a
#: hidden assumption — a real deployment would resolve the organism via
#: the UniProt connector's own record first.
_DEFAULT_SPECIES = 9606


class StringConnector:
    """Protein-protein functional association (Architecture, Layer 6 MVP
    source; CC BY 4.0, safe to cache and redistribute per
    docs/RESOURCES.md).
    """

    name = "string"
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "uniprot"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, accession = parse_curie(curie)
        resolved = get_json(
            _RESOLVE_API.format(accession=accession, species=_DEFAULT_SPECIES)
        )
        if not resolved:
            raise RuntimeError(f"STRING has no mapping for '{curie}' in species {_DEFAULT_SPECIES}")
        string_id = resolved[0]["stringId"]
        preferred_name = resolved[0]["preferredName"]

        edges = get_json(
            _NETWORK_API.format(string_id=string_id, species=_DEFAULT_SPECIES)
        )
        partners = sorted(
            {
                edge["preferredName_B"] if edge["preferredName_A"] == preferred_name else edge["preferredName_A"]
                for edge in edges
                if preferred_name in (edge["preferredName_A"], edge["preferredName_B"])
            }
        )
        return {
            "curie": curie,
            "source": "STRING",
            "license": "CC BY 4.0",
            "data": {
                "preferred_name": preferred_name,
                "string_id": string_id,
                "species": _DEFAULT_SPECIES,
                "direct_interaction_partners": partners,
            },
        }
