from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = (
    "https://omnipathdb.org/interactions"
    "?genesymbols=1&resources=CollecTRI&format=json&sources={accession}&limit=25"
)


class CollecTRIConnector:
    """Curated transcription-factor -> target regulatory network
    (Architecture, Layer 7's gene-regulation extension), accessed live via
    OmniPath's REST API — the recommended 2023+ successor to the
    now-stale DoRothEA/TRRUST per docs/RESOURCES.md. Complements
    `grn_inference`'s inferred-from-expression edges with an
    independently curated, literature-backed set.

    RegulonDB (the *E. coli*-specific curated network the roadmap also
    named) has moved to a GraphQL API with no simple queryable REST
    endpoint found in a reasonable search — deferred rather than forced;
    CollecTRI is genuinely tractable and, being human-focused, ties
    naturally to the same TP53 anchor gene Phase 3's connectors validate
    against.
    """

    name = "collectri"
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "uniprot"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, accession = parse_curie(curie)
        edges = get_json(_API.format(accession=accession))
        return {
            "curie": curie,
            "source": "CollecTRI (via OmniPath)",
            "license": "CC BY 4.0 (OmniPath); underlying CollecTRI terms per source database",
            "data": {
                "regulator_accession": accession,
                "target_count": len(edges),
                "targets": [
                    {
                        "target_genesymbol": edge.get("target_genesymbol"),
                        "target_accession": edge.get("target"),
                        "is_stimulation": edge.get("is_stimulation"),
                        "is_inhibition": edge.get("is_inhibition"),
                    }
                    for edge in edges
                ],
            },
        }
