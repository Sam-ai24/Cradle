from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = "https://www.ebi.ac.uk/biomodels/{model_id}?format=json"


class BioModelsConnector:
    """Curated SBML models (Architecture, Layer 6 MVP source; CC0, safe to
    cache and redistribute per docs/RESOURCES.md).
    """

    name = "biomodels"
    #: The same Gardner, Cantor & Collins (2000) toggle switch used as
    #: Cradle's own Phase 1 example model — this connector fetching its
    #: real BioModels record independently corroborates the CURIE Cradle
    #: already annotated that model with.
    conformance_curie = "biomodels.db:BIOMD0000000507"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "biomodels.db"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, model_id = parse_curie(curie)
        payload = get_json(_API.format(model_id=model_id))
        publication = payload.get("publication", {})
        return {
            "curie": curie,
            "source": "BioModels",
            "license": "CC0",
            "data": {
                "name": payload.get("name"),
                "curation_status": payload.get("curationStatus"),
                "format": payload.get("format", {}).get("name"),
                "publication_title": publication.get("title"),
                "pubmed_id": publication.get("accession"),
            },
        }
