from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = "https://alphafold.ebi.ac.uk/api/prediction/{accession}"


class AlphaFoldDbConnector:
    """Predicted protein structure (Architecture, Layer 6 MVP source; CC BY
    4.0, safe to cache and redistribute per docs/RESOURCES.md).

    Predictions are keyed by UniProt accession — this connector accepts
    the same `uniprot:` CURIE namespace as `UniProtConnector` and
    `StringConnector` on purpose: several MVP sources answer for the same
    entity with genuinely different data, which is exactly what
    `cradle.knowledge.router.resolve_all` fans a query out across.
    """

    name = "alphafold-db"
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "uniprot"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, accession = parse_curie(curie)
        payload = get_json(_API.format(accession=accession))[0]
        return {
            "curie": curie,
            "source": "AlphaFold DB",
            "license": "CC BY 4.0",
            "data": {
                "model_entity_id": payload.get("modelEntityId"),
                "global_plddt": payload.get("globalMetricValue"),
                "latest_version": payload.get("latestVersion"),
                "cif_url": payload.get("cifUrl"),
                "pdb_url": payload.get("pdbUrl"),
            },
        }
