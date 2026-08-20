from __future__ import annotations

import os

from cradle.contracts.data_connector import ConnectorRecord
from cradle.contracts.errors import NotConfiguredError
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = (
    "https://webservice.thebiogrid.org/interactions/"
    "?accesskey={api_key}&format=json&searchIds=true&geneList={accession}"
    "&species={species}&max=25"
)
_DEFAULT_SPECIES = 9606
_API_KEY_ENV_VAR = "CRADLE_BIOGRID_API_KEY"


class MissingApiKeyError(NotConfiguredError):
    pass


class BioGridConnector:
    """Protein-protein interaction (Architecture, Layer 6 MVP source; MIT
    — the cleanest license of the interaction databases per
    docs/RESOURCES.md — but access requires a free registered API key,
    unlike UniProt/PDB/Reactome/BioModels/STRING which need none).

    Requires a real key (BioGRID's own registration, not a Cradle
    license-gate acknowledgment — this is an access-control requirement,
    not a redistribution restriction) via the `CRADLE_BIOGRID_API_KEY`
    environment variable. Built against BioGRID's documented REST API
    shape; unlike the other six MVP connectors, not live-verified in this
    session since no key was available to test with — flagged here rather
    than presented as confirmed.
    """

    name = "biogrid"
    conformance_curie = "uniprot:P04637"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "uniprot"

    def fetch(self, curie: str) -> ConnectorRecord:
        api_key = os.environ.get(_API_KEY_ENV_VAR)
        if not api_key:
            raise MissingApiKeyError(
                f"BioGRID requires a free registered API key — set {_API_KEY_ENV_VAR} "
                f"(register at https://webservice.thebiogrid.org)."
            )
        _, accession = parse_curie(curie)
        payload = get_json(
            _API.format(api_key=api_key, accession=accession, species=_DEFAULT_SPECIES)
        )
        interactions = list(payload.values()) if isinstance(payload, dict) else []
        return {
            "curie": curie,
            "source": "BioGRID",
            "license": "MIT",
            "data": {
                "queried_uniprot_accession": accession,
                "interaction_count": len(interactions),
                "interactions": [
                    {
                        "official_symbol_a": i.get("OFFICIAL_SYMBOL_A"),
                        "official_symbol_b": i.get("OFFICIAL_SYMBOL_B"),
                        "experimental_system": i.get("EXPERIMENTAL_SYSTEM"),
                    }
                    for i in interactions[:10]
                ],
            },
        }
