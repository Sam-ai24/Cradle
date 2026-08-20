from __future__ import annotations

import antimony
import libsbml


class ModelCompilationError(RuntimeError):
    pass


def antimony_to_sbml_document(antimony_text: str) -> libsbml.SBMLDocument:
    """Compile Antimony source to an `SBMLDocument`, validated via libsbml.

    Returns the parsed, mutable document (so callers can attach MIRIAM
    annotations with `cradle.substrate.annotate` before serializing) rather
    than a raw string. Raises `ModelCompilationError` if Antimony fails to
    load the module or the resulting SBML fails libsbml's own consistency
    checks.
    """
    antimony.clearPreviousLoads()
    code = antimony.loadAntimonyString(antimony_text)
    if code < 0:
        raise ModelCompilationError(antimony.getLastError())

    module_name = antimony.getMainModuleName()
    sbml_str = antimony.getSBMLString(module_name)
    if not sbml_str:
        raise ModelCompilationError(f"Antimony produced no SBML for module '{module_name}'")

    document = libsbml.readSBMLFromString(sbml_str)
    errors = [
        document.getError(i).getMessage()
        for i in range(document.getNumErrors())
        if document.getError(i).getSeverity() >= libsbml.LIBSBML_SEV_ERROR
    ]
    if errors:
        raise ModelCompilationError("SBML validation failed: " + "; ".join(errors))

    return document


def write_sbml(document: libsbml.SBMLDocument, path: str) -> str:
    if not libsbml.writeSBMLToFile(document, path):
        raise ModelCompilationError(f"libsbml failed to write SBML to '{path}'")
    return path
