from __future__ import annotations

import libsbml

from cradle.substrate.annotate import annotate_with_curie, require_entity_annotations
from cradle.substrate.model import antimony_to_sbml_document

#: The genetic toggle switch from Gardner, Cantor & Collins (2000), "Construction
#: of a genetic toggle switch in Escherichia coli", Nature 403:339-342
#: (doi:10.1038/35002131), curated in BioModels as BIOMD0000000507. U and V are
#: the dimensionless concentrations of the two mutually-repressing proteins
#: (Repressor 1 = LacI, Repressor 2 = the bacteriophage lambda CI repressor, per
#: the original construct); alpha1, alpha2, beta, gam are the paper's fitted
#: nominal dimensionless parameter values, not invented for this example.
ANTIMONY_SOURCE = """
model toggle_switch()
  species U, V;

  J1: -> U; alpha1 / (1 + V^beta);
  J2: U -> ; U;
  J3: -> V; alpha2 / (1 + U^gam);
  J4: V -> ; V;

  alpha1 = 156.25;
  alpha2 = 15.6;
  beta = 2.5;
  gam = 1.0;

  U = 0.2;
  V = 0.4;
end
"""

#: Source-of-truth CURIEs. `_SOURCE` is "described by" the model/paper (a
#: provenance reference, not an identity claim); `_LACI`/`_LAMBDA_CI` are
#: "is" claims about what the two species represent.
_SOURCE_MODEL = "biomodels.db:BIOMD0000000507"
_SOURCE_PAPER = "doi:10.1038/35002131"
_LACI = "uniprot:P03023"
_LAMBDA_CI = "uniprot:P03034"


def build_annotated_document() -> libsbml.SBMLDocument:
    """Compile the toggle switch and attach a MIRIAM/CURIE annotation to
    every species, parameter, and reaction, then verify none were missed.
    """
    document = antimony_to_sbml_document(ANTIMONY_SOURCE)
    model = document.getModel()

    annotate_with_curie(model.getSpecies("U"), _LACI, libsbml.BQB_IS)
    annotate_with_curie(model.getSpecies("V"), _LAMBDA_CI, libsbml.BQB_IS)

    for parameter_id in ("alpha1", "alpha2", "beta", "gam"):
        annotate_with_curie(
            model.getParameter(parameter_id), _SOURCE_MODEL, libsbml.BQB_IS_DESCRIBED_BY
        )

    for reaction_id in ("J1", "J2", "J3", "J4"):
        annotate_with_curie(
            model.getReaction(reaction_id), _SOURCE_PAPER, libsbml.BQB_IS_DESCRIBED_BY
        )

    require_entity_annotations(model)
    return document
