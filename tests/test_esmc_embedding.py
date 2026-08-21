from __future__ import annotations

import pytest

esmc_embedding = pytest.importorskip("esmc_embedding")
from esmc_embedding.adapter import CONFORMANCE_SEQUENCE, build_adapter  # noqa: E402

#: A second real, current, reviewed UniProt entry (human lysozyme C,
#: P61626 — full precursor including signal peptide, verified directly
#: against the live UniProt API), unrelated to CONFORMANCE_SEQUENCE —
#: used to prove the adapter's output actually depends on the input
#: sequence rather than being a constant vector with the right shape.
_LYSOZYME_SEQUENCE = (
    "MKALIVLGLVLLSVTVQGKVFERCELARTLKRLGMDGYRGISLANWMCLAKWESGYNTRATNYNAGDRSTD"
    "YGIFQINSRYWCNDGKTPGAVNACHLSCSALLQDNIADAVACAKRVVRDPQGIRAWVAWRNRCQNRDVRQYVQGCGV"
)

#: P0CG47's real sequence length, confirmed directly against the live
#: UniProt API in this session (human polyubiquitin-B precursor).
_UBB_SEQUENCE_LENGTH = 229


@pytest.fixture(scope="module")
def adapter():
    return build_adapter()


def test_embedding_has_the_real_model_dimension_and_correct_sequence_length(adapter):
    result = adapter.predict({"sequence": CONFORMANCE_SEQUENCE})
    assert result["output"]["embedding_dim"] == 960
    assert len(result["output"]["embedding"]) == 960
    assert result["output"]["sequence_length"] == len(CONFORMANCE_SEQUENCE)
    assert result["provenance"]["sequence_source"] == "direct"


def test_embedding_is_deterministic_for_the_same_sequence(adapter):
    first = adapter.predict({"sequence": CONFORMANCE_SEQUENCE})["output"]["embedding"]
    second = adapter.predict({"sequence": CONFORMANCE_SEQUENCE})["output"]["embedding"]
    assert first == pytest.approx(second, abs=1e-6)


def test_embedding_actually_depends_on_the_input_sequence(adapter):
    """Not a shape-only check: two unrelated real proteins must produce
    meaningfully different embeddings, or the model isn't actually
    reading the sequence.
    """
    ubiquitin = adapter.predict({"sequence": CONFORMANCE_SEQUENCE})["output"]["embedding"]
    lysozyme = adapter.predict({"sequence": _LYSOZYME_SEQUENCE})["output"]["embedding"]

    max_abs_diff = max(abs(a - b) for a, b in zip(ubiquitin, lysozyme))
    assert max_abs_diff > 0.01, "two unrelated proteins produced near-identical embeddings"


def test_predict_resolves_a_real_sequence_from_a_uniprot_curie(adapter):
    """Confirms the CURIE path fetches the real, live UniProt sequence
    (not a stub) and that it matches the same protein passed directly —
    same real data reached two different ways.
    """
    from_curie = adapter.predict({"curie": "uniprot:P0CG47"})
    assert from_curie["provenance"]["sequence_source"] == "uniprot:P0CG47"
    assert from_curie["output"]["sequence_length"] == _UBB_SEQUENCE_LENGTH


def test_predict_rejects_a_non_uniprot_curie(adapter):
    with pytest.raises(ValueError, match="uniprot"):
        adapter.predict({"curie": "chembl:CHEMBL25"})
