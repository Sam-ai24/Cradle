from __future__ import annotations

from cradle.knowledge.resolver import resolve_curie
from cradle.knowledge.router import resolve_all

#: TP53 — chosen because, unlike Phase 1's bacterial toggle-switch proteins,
#: it has real coverage across every MVP source: UniProt, PDB, AlphaFold DB,
#: Reactome, and STRING all have genuine data for this gene.
GENE_CURIE = "uniprot:P04637"


def test_gene_query_resolves_across_at_least_three_mvp_sources():
    """Phase 3 exit criterion: a query like "give me everything known
    about gene X" resolves across at least 3 of the MVP sources and
    returns CURIE-linked, source-attributed data — without the caller
    naming which connectors to use.
    """
    results = resolve_all(GENE_CURIE)

    successful = {
        name: record
        for name, record in results.items()
        if "error" not in record and name != "hello"
    }
    assert len(successful) >= 3, (
        f"expected at least 3 real MVP sources to answer, got {list(successful)} "
        f"(full results: {results})"
    )

    for name, record in successful.items():
        assert record["curie"] == GENE_CURIE, f"{name} did not echo back the queried CURIE"
        assert record["source"], f"{name} record has no source attribution"
        assert record["license"], f"{name} record has no license attribution"
        assert record["data"], f"{name} record has no data"


def test_curie_resolves_via_identifiers_org_independent_of_any_connector():
    """The resolver works for a CURIE regardless of whether Cradle has a
    connector for its namespace — this is the "any CURIE is traceable"
    guarantee, not something scoped to the MVP connector list.
    """
    resolved = resolve_curie(GENE_CURIE)
    assert resolved
    assert any("uniprot" in entry.get("compactIdentifierResolvedUrl", "").lower() for entry in resolved)
