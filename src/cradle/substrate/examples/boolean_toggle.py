from __future__ import annotations

import libsbml

#: A synthetic, illustrative Boolean regulatory toggle — the qualitative
#: analogue of the continuous Gardner et al. (2000) toggle switch Phase 1
#: uses, but not sourced from it (mutual repression collapses to
#: different, simpler dynamics in the Boolean abstraction). Two genes
#: mutually repress each other: A(t+1) = NOT B(t), B(t+1) = NOT A(t).
#: Under synchronous update this has two fixed points ((1,0) and (0,1))
#: and one period-2 cycle ((1,1) <-> (0,0)) — a real, checkable dynamical
#: fact used to validate the executor, not asserted without proof.


def _add_species(qual_plugin, species_id: str, initial_level: int) -> None:
    species = qual_plugin.createQualitativeSpecies()
    species.setId(species_id)
    species.setCompartment("cell")
    species.setConstant(False)
    species.setInitialLevel(initial_level)
    species.setMaxLevel(1)


def _add_repression_transition(qual_plugin, target: str, regulator: str) -> None:
    transition = qual_plugin.createTransition()
    transition.setId(f"tr_{target}")

    transition_input = transition.createInput()
    transition_input.setId(f"in_{target}_{regulator}")
    transition_input.setQualitativeSpecies(regulator)
    transition_input.setSign(libsbml.INPUT_SIGN_NEGATIVE)
    transition_input.setTransitionEffect(libsbml.INPUT_TRANSITION_EFFECT_NONE)

    output = transition.createOutput()
    output.setId(f"out_{target}")
    output.setQualitativeSpecies(target)
    output.setTransitionEffect(libsbml.OUTPUT_TRANSITION_EFFECT_ASSIGNMENT_LEVEL)

    function_term = transition.createFunctionTerm()
    function_term.setResultLevel(1)
    function_term.setMath(libsbml.parseFormula(f"eq({regulator}, 0)"))

    transition.createDefaultTerm().setResultLevel(0)


def build_document(initial_a: int = 1, initial_b: int = 1) -> libsbml.SBMLDocument:
    document = libsbml.SBMLDocument(3, 1)
    # Order matters: setPackageRequired() is a no-op if called before the
    # package is enabled (confirmed by testing — it silently doesn't set
    # the attribute, which then fails SBML validation downstream).
    document.enablePackage(libsbml.QualExtension.getXmlnsL3V1V1(), "qual", True)
    document.setPackageRequired("qual", True)

    model = document.createModel()
    model.setId("boolean_toggle")
    compartment = model.createCompartment()
    compartment.setId("cell")
    compartment.setConstant(True)

    qual_plugin = model.getPlugin("qual")
    _add_species(qual_plugin, "A", initial_a)
    _add_species(qual_plugin, "B", initial_b)
    _add_repression_transition(qual_plugin, "A", "B")
    _add_repression_transition(qual_plugin, "B", "A")
    return document


def write_sbml(path: str, initial_a: int = 1, initial_b: int = 1) -> str:
    document = build_document(initial_a, initial_b)
    if not libsbml.writeSBMLToFile(document, path):
        raise RuntimeError(f"libsbml failed to write the Boolean toggle model to '{path}'")
    return path
