from __future__ import annotations

from pathlib import Path

import libcombine

#: Standard COMBINE "known format" URNs (combine-org/combine-specifications).
SBML_FORMAT = "http://identifiers.org/combine.specifications/sbml"
SEDML_FORMAT = "http://identifiers.org/combine.specifications/sed-ml"


class ArchiveError(RuntimeError):
    pass


def package_combine_archive(
    output_path: str,
    sbml_path: str,
    sbml_target_name: str,
    sedml_path: str,
    sedml_target_name: str,
) -> str:
    """Bundle one SBML model and one SED-ML experiment into a COMBINE/OMEX
    archive at `output_path` (Architecture Layer 3). The SED-ML file is the
    archive's master file — it's the entry point a BioSimulators-style
    execution adapter (Layer 4) looks for.
    """
    archive = libcombine.CombineArchive()
    if not archive.addFile(sbml_path, sbml_target_name, SBML_FORMAT, False):
        raise ArchiveError(f"failed to add SBML file '{sbml_path}' to archive")
    if not archive.addFile(sedml_path, sedml_target_name, SEDML_FORMAT, True):
        raise ArchiveError(f"failed to add SED-ML file '{sedml_path}' to archive")
    if not archive.writeToFile(output_path):
        raise ArchiveError(f"failed to write COMBINE archive to '{output_path}'")
    return output_path


def extract_combine_archive(archive_path: str, destination_dir: str) -> str:
    """Extract a COMBINE archive to `destination_dir` and return the on-disk
    path to its master file (the SED-ML experiment, by construction of
    `package_combine_archive`). Adapters without a reliable native COMBINE/
    SED-ML importer extract to disk and drive their own engine directly,
    rather than depending on that importer's completeness.
    """
    reader = libcombine.CombineArchive()
    if not reader.initializeFromArchive(archive_path):
        raise ArchiveError(f"failed to open COMBINE archive '{archive_path}'")

    master = reader.getMasterFile()
    if master is None:
        raise ArchiveError(f"COMBINE archive '{archive_path}' has no master file")
    master_location = master.getLocation()

    if not reader.extractTo(destination_dir):
        raise ArchiveError(f"failed to extract COMBINE archive '{archive_path}' to '{destination_dir}'")

    return str(Path(destination_dir) / master_location)
