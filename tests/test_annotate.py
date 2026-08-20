from __future__ import annotations

import pytest

from cradle.substrate.annotate import (
    InvalidCurieError,
    MissingAnnotationError,
    curie_to_uri,
    require_entity_annotations,
)
from cradle.substrate.model import antimony_to_sbml_document

UNANNOTATED_MODEL = """
model unannotated()
  species A, B;
  J1: A -> B; k1*A;
  k1 = 0.5;
  A = 10;
end
"""


def test_curie_to_uri_accepts_real_curies():
    assert curie_to_uri("uniprot:P03023") == "https://identifiers.org/uniprot:P03023"
    assert curie_to_uri("doi:10.1038/35002131") == "https://identifiers.org/doi:10.1038/35002131"


def test_curie_to_uri_rejects_malformed_input():
    with pytest.raises(InvalidCurieError):
        curie_to_uri("not-a-curie")


def test_require_entity_annotations_rejects_unannotated_model():
    document = antimony_to_sbml_document(UNANNOTATED_MODEL)
    with pytest.raises(MissingAnnotationError) as exc_info:
        require_entity_annotations(document.getModel())
    # every species, parameter, and reaction should be named as missing
    for entity_id in ("A", "B", "k1", "J1"):
        assert entity_id in str(exc_info.value)
