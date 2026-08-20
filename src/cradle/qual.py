from __future__ import annotations

from dataclasses import dataclass

import libsbml

#: SBML `qual` (Level 3 qualitative-models package) sits alongside SBML
#: core at Layer 1 for Boolean/qualitative gene-regulatory models. No
#: mature registered engine executes it the way COPASI/Tellurium execute
#: continuous kinetics (Architecture, Layer 1/4), so this module both
#: reads the standard and provides Cradle's own execution semantics —
#: synchronous Boolean-network update, the simplest and most common
#: convention for this model class.

_RELATIONAL_OPS = {
    libsbml.AST_RELATIONAL_EQ: lambda a, b: a == b,
    libsbml.AST_RELATIONAL_NEQ: lambda a, b: a != b,
    libsbml.AST_RELATIONAL_GT: lambda a, b: a > b,
    libsbml.AST_RELATIONAL_GEQ: lambda a, b: a >= b,
    libsbml.AST_RELATIONAL_LT: lambda a, b: a < b,
    libsbml.AST_RELATIONAL_LEQ: lambda a, b: a <= b,
}

_LOGICAL_OPS = {
    libsbml.AST_LOGICAL_AND: all,
    libsbml.AST_LOGICAL_OR: any,
}


class QualEvaluationError(ValueError):
    pass


def evaluate_math(node: libsbml.ASTNode, levels: dict[str, int]) -> bool:
    """Evaluate an SBML-qual functionTerm's MathML condition against the
    current species levels. Supports the relational ops (eq/neq/gt/geq/
    lt/leq), and/or, not, and integer/species-name leaves — the subset
    actually needed to express Boolean regulatory logic, not the full
    generality of SBML's MathML (no arithmetic, no piecewise, no xor —
    add if a real model needs them).
    """
    node_type = node.getType()

    if node_type == libsbml.AST_NAME:
        return levels[node.getName()]
    if node_type in (libsbml.AST_INTEGER, libsbml.AST_REAL):
        return node.getInteger() if node_type == libsbml.AST_INTEGER else node.getReal()

    if node_type in _RELATIONAL_OPS:
        left = evaluate_math(node.getChild(0), levels)
        right = evaluate_math(node.getChild(1), levels)
        return _RELATIONAL_OPS[node_type](left, right)

    if node_type in _LOGICAL_OPS:
        children = [evaluate_math(node.getChild(i), levels) for i in range(node.getNumChildren())]
        return _LOGICAL_OPS[node_type](children)

    if node_type == libsbml.AST_LOGICAL_NOT:
        return not evaluate_math(node.getChild(0), levels)

    raise QualEvaluationError(f"unsupported MathML node type: {node_type}")


@dataclass
class QualSpecies:
    species_id: str
    initial_level: int
    max_level: int


@dataclass
class QualTransition:
    target_species_id: str
    #: (condition_ast, result_level) pairs, evaluated in document order —
    #: first match wins, matching SBML-qual's own functionTerm semantics.
    function_terms: list[tuple[libsbml.ASTNode, int]]
    default_level: int

    def evaluate(self, levels: dict[str, int]) -> int:
        for condition, result_level in self.function_terms:
            if evaluate_math(condition, levels):
                return result_level
        return self.default_level


@dataclass
class QualModel:
    species: list[QualSpecies]
    transitions: list[QualTransition]

    def initial_levels(self) -> dict[str, int]:
        return {s.species_id: s.initial_level for s in self.species}

    def step(self, levels: dict[str, int]) -> dict[str, int]:
        """One synchronous update: every transition's next level is
        computed from the *current* levels (not partially-updated ones),
        then all species update together — the standard convention for
        Boolean network simulation.
        """
        by_target = {t.target_species_id: t for t in self.transitions}
        next_levels = dict(levels)
        for species_id, current_level in levels.items():
            transition = by_target.get(species_id)
            if transition is not None:
                next_levels[species_id] = transition.evaluate(levels)
            # species with no transition stay constant, matching SBML-qual's
            # "qual:constant" convention for boundary/input species.
        return next_levels


def read_qual_model(sbml_path: str) -> QualModel:
    document = libsbml.readSBMLFromFile(sbml_path)
    errors = [
        document.getError(i).getMessage()
        for i in range(document.getNumErrors())
        if document.getError(i).getSeverity() >= libsbml.LIBSBML_SEV_ERROR
    ]
    if errors:
        raise QualEvaluationError("SBML validation failed: " + "; ".join(errors))

    model = document.getModel()
    qual_plugin = model.getPlugin("qual")
    if qual_plugin is None:
        raise QualEvaluationError(f"'{sbml_path}' has no SBML qual package data")

    species = [
        QualSpecies(
            species_id=qs.getId(),
            initial_level=qs.getInitialLevel(),
            max_level=qs.getMaxLevel(),
        )
        for qs in qual_plugin.getListOfQualitativeSpecies()
    ]

    transitions = []
    for transition in qual_plugin.getListOfTransitions():
        outputs = list(transition.getListOfOutputs())
        if len(outputs) != 1:
            raise QualEvaluationError(
                f"transition '{transition.getId()}' has {len(outputs)} outputs; "
                f"only single-output transitions are supported"
            )
        # .deepCopy() detaches each ASTNode from the SBMLDocument's object
        # tree — without it, the math nodes become dangling pointers once
        # `document` goes out of scope at the end of this function (a real
        # SWIG lifetime bug caught here: garbage getType() values on
        # evaluation, not at parse time, since Python's GC timing is what
        # actually frees the underlying C++ memory).
        function_terms = [
            (ft.getMath().deepCopy(), ft.getResultLevel())
            for ft in transition.getListOfFunctionTerms()
        ]
        default_term = transition.getDefaultTerm()
        transitions.append(
            QualTransition(
                target_species_id=outputs[0].getQualitativeSpecies(),
                function_terms=function_terms,
                default_level=default_term.getResultLevel() if default_term else 0,
            )
        )

    return QualModel(species=species, transitions=transitions)
