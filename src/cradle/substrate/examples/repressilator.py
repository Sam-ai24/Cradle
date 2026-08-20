from __future__ import annotations

import libsbml

from cradle.knowledge.http import get_text
from cradle.substrate.annotate import annotate_with_curie, require_entity_annotations

#: Elowitz & Leibler (2000), "A synthetic oscillatory network of
#: transcriptional regulators", Nature 403:335-338 (PMID 10659856) —
#: published back-to-back with the Gardner toggle switch (PMID 10659857)
#: Phase 1 already uses. Curated in BioModels as BIOMD0000000012. Unlike
#: the hand-authored toggle switch, this model is ingested directly from
#: its real, independently curated source, via the Phase 3 knowledge
#: layer's HTTP client — the first model Cradle didn't author itself.
_MODEL_ID = "BIOMD0000000012"
_DOWNLOAD_URL = (
    f"https://www.ebi.ac.uk/biomodels/model/download/{_MODEL_ID}"
    f"?filename={_MODEL_ID}_url.xml"
)
_SOURCE_MODEL_CURIE = f"biomodels.db:{_MODEL_ID}"

SPECIES_IDS = ["PX", "PY", "PZ"]  # LacI, TetR, cI protein levels


def download_source_sbml() -> str:
    """Fetch the real, currently-curated SBML text from BioModels."""
    return get_text(_DOWNLOAD_URL)


def build_annotated_document(sbml_text: str | None = None) -> libsbml.SBMLDocument:
    """Parse the BioModels SBML and close the one annotation gap it has by
    Cradle's stricter bar: BioModels curated every species and reaction
    with a real MIRIAM CVTerm, but left all 16 kinetic parameters
    unannotated. This supplements each with a "described by" reference to
    the same curated model record — an honest claim, since that record is
    genuinely where the fitted values came from — and then verifies the
    gap is actually closed via `require_entity_annotations`, the same
    mechanical check Phase 1 uses, rather than trusting the source's own
    curation to already satisfy Cradle's rule.
    """
    if sbml_text is None:
        sbml_text = download_source_sbml()

    document = libsbml.readSBMLFromString(sbml_text)
    errors = [
        document.getError(i).getMessage()
        for i in range(document.getNumErrors())
        if document.getError(i).getSeverity() >= libsbml.LIBSBML_SEV_ERROR
    ]
    if errors:
        raise ValueError("SBML validation failed: " + "; ".join(errors))

    model = document.getModel()
    for parameter in model.getListOfParameters():
        if parameter.getNumCVTerms() == 0:
            annotate_with_curie(
                parameter, _SOURCE_MODEL_CURIE, libsbml.BQB_IS_DESCRIBED_BY
            )

    require_entity_annotations(model)
    return document
