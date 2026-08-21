from __future__ import annotations

import pytest

pubchem_data = pytest.importorskip("pubchem_data")
from pubchem_data.connector import PubChemConnector  # noqa: E402

#: Aspirin, PubChem CID 2244 — a real, permanently-stable compound record.
#: Molecular formula C9H8O4 and molecular weight ~180.16 g/mol are
#: textbook ground-truth facts (also independently confirmed directly
#: against the live PubChem PUG REST API in this session), not values
#: this connector could satisfy by returning a correctly-shaped stub.
_ASPIRIN_CURIE = "pubchem.compound:2244"
_ASPIRIN_FORMULA = "C9H8O4"
_ASPIRIN_WEIGHT = 180.16

#: Caffeine, PubChem CID 2519 — a second real, unrelated compound, used to
#: prove the connector's output actually depends on the CURIE it's given
#: rather than being a constant record with the right shape.
_CAFFEINE_CURIE = "pubchem.compound:2519"
_CAFFEINE_FORMULA = "C8H10N4O2"


@pytest.fixture(scope="module")
def connector():
    return PubChemConnector()


def test_fetch_returns_the_real_ground_truth_formula_and_weight_for_aspirin(connector):
    record = connector.fetch(_ASPIRIN_CURIE)
    assert record["curie"] == _ASPIRIN_CURIE
    assert record["data"]["molecular_formula"] == _ASPIRIN_FORMULA
    assert float(record["data"]["molecular_weight"]) == pytest.approx(_ASPIRIN_WEIGHT, abs=0.01)
    # Real license, not a placeholder.
    assert "public domain" in record["license"].lower()


def test_fetch_actually_depends_on_the_curie_not_a_constant_stub(connector):
    """Not a shape-only check: two unrelated real compounds must produce
    genuinely different formulas, or the connector isn't actually
    resolving the CID it's given.
    """
    aspirin = connector.fetch(_ASPIRIN_CURIE)
    caffeine = connector.fetch(_CAFFEINE_CURIE)

    assert aspirin["data"]["molecular_formula"] == _ASPIRIN_FORMULA
    assert caffeine["data"]["molecular_formula"] == _CAFFEINE_FORMULA
    assert aspirin["data"]["molecular_formula"] != caffeine["data"]["molecular_formula"]
    assert aspirin["data"]["cid"] != caffeine["data"]["cid"]


def test_fetch_rejects_a_non_pubchem_curie(connector):
    with pytest.raises(ValueError, match="pubchem.compound"):
        connector.fetch("uniprot:P04637")


def test_fetch_rejects_a_nonexistent_cid(connector):
    # 999999999 is syntactically a valid CID but was never assigned a
    # compound. PubChem's PUG REST quirk (confirmed directly against the
    # live API): this returns HTTP 200 with a Properties entry that only
    # echoes "CID" and omits every property that was actually requested,
    # rather than a clean 404 — the connector must still treat it as
    # not-found instead of returning a record full of Nones.
    with pytest.raises(ValueError, match="no compound record"):
        connector.fetch("pubchem.compound:999999999")
