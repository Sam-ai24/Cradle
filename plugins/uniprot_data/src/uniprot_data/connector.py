from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = "https://rest.uniprot.org/uniprotkb/{accession}.json"


class UniProtConnector:
    """Protein sequence/function (Architecture, Layer 6 MVP source; CC BY
    4.0, safe to cache and redistribute per docs/RESOURCES.md).
    """

    name = "uniprot"
    #: TP53 — a real, well-annotated entry, used to conformance-test this
    #: connector against the live API rather than a placeholder identifier.
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "uniprot"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, accession = parse_curie(curie)
        payload = get_json(_API.format(accession=accession))
        recommended_name = (
            payload.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value")
        )
        organism = payload.get("organism", {}).get("scientificName")
        return {
            "curie": curie,
            "source": "UniProt",
            "license": "CC BY 4.0",
            "data": {
                "accession": payload.get("primaryAccession"),
                "entry_name": payload.get("uniProtkbId"),
                "recommended_name": recommended_name,
                "organism": organism,
                "sequence_length": payload.get("sequence", {}).get("length"),
            },
        }
