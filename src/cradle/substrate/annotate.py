from __future__ import annotations

import re

import libsbml

#: `namespace:localId`, e.g. "uniprot:P03023", "biomodels.db:BIOMD0000000507",
#: or "doi:10.1038/35002131" (DOIs legitimately contain a slash in the local
#: ID). Deliberately conservative — matches identifiers.org prefix
#: conventions (lowercase, dots allowed) without validating against the live
#: registry here; that's a Layer 6 data-connector concern, not this module's.
_CURIE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._:/-]*$")


class InvalidCurieError(ValueError):
    pass


class MissingAnnotationError(AssertionError):
    """Raised when an SBML entity has no MIRIAM/CURIE annotation (Layer 8: no
    unsourced numbers)."""


def parse_curie(curie: str) -> tuple[str, str]:
    """Split `namespace:localId` into its two parts, validating the same
    syntax rule `curie_to_uri` uses. Shared with the Layer 6 knowledge
    layer (`cradle.knowledge`) so both layers agree on one CURIE grammar.
    """
    if not _CURIE_RE.match(curie):
        raise InvalidCurieError(f"'{curie}' is not a valid CURIE (expected namespace:localId)")
    namespace, local_id = curie.split(":", 1)
    return namespace, local_id


def curie_to_uri(curie: str) -> str:
    parse_curie(curie)
    return f"https://identifiers.org/{curie}"


def annotate_with_curie(
    sbase: libsbml.SBase,
    curie: str,
    qualifier: int = libsbml.BQB_IS,
) -> None:
    """Attach a MIRIAM-style biological-qualifier CVTerm pointing at `curie`.

    `qualifier` defaults to "is" (BQB_IS); pass e.g. `libsbml.BQB_IS_DESCRIBED_BY`
    for a literature reference (a DOI/PubMed CURIE) rather than an identity claim.
    """
    uri = curie_to_uri(curie)
    if not sbase.isSetMetaId():
        sbase.setMetaId(f"{sbase.getId()}_meta")

    cv = libsbml.CVTerm()
    cv.setQualifierType(libsbml.BIOLOGICAL_QUALIFIER)
    cv.setBiologicalQualifierType(qualifier)
    cv.addResource(uri)
    result = sbase.addCVTerm(cv)
    if result != libsbml.LIBSBML_OPERATION_SUCCESS:
        raise RuntimeError(f"libsbml.addCVTerm failed for '{sbase.getId()}' (code {result})")


def _all_annotatable_entities(model: libsbml.Model) -> list[libsbml.SBase]:
    entities: list[libsbml.SBase] = []
    entities.extend(model.getListOfSpecies())
    entities.extend(model.getListOfParameters())
    entities.extend(model.getListOfReactions())
    return entities


def require_entity_annotations(model: libsbml.Model) -> None:
    """Raise MissingAnnotationError if any species, parameter, or reaction in
    `model` has zero CVTerms. This is Layer 1/8's "no entity without a source
    annotation" rule, enforced mechanically rather than by convention.
    """
    unannotated = [
        entity.getId()
        for entity in _all_annotatable_entities(model)
        if entity.getNumCVTerms() == 0
    ]
    if unannotated:
        raise MissingAnnotationError(
            "entities missing a MIRIAM/CURIE annotation: " + ", ".join(unannotated)
        )
