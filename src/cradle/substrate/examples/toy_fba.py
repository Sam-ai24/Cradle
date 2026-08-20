from __future__ import annotations

import libsbml

#: A synthetic, illustrative constraint-based (flux-balance) model — unlike
#: `toggle_switch.py`, this is NOT sourced from a real published network and
#: is intentionally not run through `annotate.require_entity_annotations()`.
#: Its only purpose is to prove the COBRApy adapter's subprocess-isolated
#: execution path (Architecture, Layer 4/8: GPL-licensed engines stay
#: process/container-isolated) end to end with a hand-verifiable answer:
#: a linear uptake -> conversion -> secretion pathway whose optimal
#: secretion flux is bounded by, and therefore must equal, the uptake bound.
UPTAKE_BOUND = 10.0
EXPECTED_OPTIMAL_SECRETION_FLUX = UPTAKE_BOUND


def build_document() -> libsbml.SBMLDocument:
    document = libsbml.SBMLDocument(3, 2)
    document.setPackageRequired("fbc", False)
    document.enablePackage(libsbml.FbcExtension.getXmlnsL3V1V2(), "fbc", True)

    model = document.createModel()
    model.setId("toy_fba")
    model_fbc = model.getPlugin("fbc")
    model_fbc.setStrict(True)

    compartment = model.createCompartment()
    compartment.setId("c")
    compartment.setConstant(True)
    compartment.setSize(1.0)
    compartment.setSpatialDimensions(3)

    for species_id in ("S", "P"):
        species = model.createSpecies()
        species.setId(species_id)
        species.setCompartment("c")
        species.setConstant(False)
        species.setBoundaryCondition(False)
        species.setHasOnlySubstanceUnits(False)
        species.getPlugin("fbc").setCharge(0)

    def add_bound(parameter_id: str, value: float) -> None:
        parameter = model.createParameter()
        parameter.setId(parameter_id)
        parameter.setValue(value)
        parameter.setConstant(True)

    add_bound("lb_zero", 0.0)
    add_bound("ub_uptake", UPTAKE_BOUND)
    add_bound("ub_unconstrained", 1000.0)

    def add_reaction(
        reaction_id: str,
        reactants: list[tuple[str, float]],
        products: list[tuple[str, float]],
        upper_bound_id: str,
    ) -> None:
        reaction = model.createReaction()
        reaction.setId(reaction_id)
        reaction.setReversible(False)
        reaction.setFast(False)
        for species_id, stoichiometry in reactants:
            reactant = reaction.createReactant()
            reactant.setSpecies(species_id)
            reactant.setStoichiometry(stoichiometry)
            reactant.setConstant(True)
        for species_id, stoichiometry in products:
            product = reaction.createProduct()
            product.setSpecies(species_id)
            product.setStoichiometry(stoichiometry)
            product.setConstant(True)
        reaction_fbc = reaction.getPlugin("fbc")
        reaction_fbc.setLowerFluxBound("lb_zero")
        reaction_fbc.setUpperFluxBound(upper_bound_id)

    add_reaction("uptake", [], [("S", 1)], "ub_uptake")
    add_reaction("conversion", [("S", 1)], [("P", 1)], "ub_unconstrained")
    add_reaction("secretion", [("P", 1)], [], "ub_unconstrained")

    objective = model_fbc.createObjective()
    objective.setId("maximize_secretion")
    objective.setType("maximize")
    model_fbc.setActiveObjectiveId("maximize_secretion")
    flux_objective = objective.createFluxObjective()
    flux_objective.setReaction("secretion")
    flux_objective.setCoefficient(1.0)

    return document


def write_sbml(path: str) -> str:
    document = build_document()
    if not libsbml.writeSBMLToFile(document, path):
        raise RuntimeError(f"libsbml failed to write the toy FBA model to '{path}'")
    return path
