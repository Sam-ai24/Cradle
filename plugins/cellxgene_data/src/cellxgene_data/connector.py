from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_API = "https://api.cellxgene.cziscience.com/curation/v1/collections/{collection_id}"


class CellxgeneDiscoverConnector:
    """Single-cell dataset/collection metadata via the CZ CELLxGENE
    Discover REST API (Architecture, Layer 6 MVP source; code MIT, data
    CC-BY per docs/RESOURCES.md).

    Deliberately uses the lightweight Discover API, not the full Census
    array-data client (`cellxgene-census`/TileDB-SOMA) — Census's access
    pattern is bulk single-cell matrices, not a per-entity REST lookup, so
    it doesn't fit the `fetch(curie)` contract the way a dataset/collection
    lookup does (see docs/RESOURCES.md's note on this). CURIEs here
    address a collection by its Discover UUID, not a gene or protein.
    """

    name = "cellxgene"
    #: A real public collection (adult human retina atlas), used to
    #: conformance-test against the live API.
    conformance_curie = "cellxgene.collection:af893e86-8e9f-41f1-a474-ef05359b1fb7"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "cellxgene.collection"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, collection_id = parse_curie(curie)
        payload = get_json(_API.format(collection_id=collection_id))
        return {
            "curie": curie,
            "source": "CZ CELLxGENE Discover",
            "license": "CC-BY (data), MIT (code)",
            "data": {
                "name": payload.get("name"),
                "consortia": payload.get("consortia"),
                "dataset_count": len(payload.get("datasets", [])),
                "doi": payload.get("doi"),
            },
        }
