from __future__ import annotations

import json
import tempfile
from pathlib import Path

import libcombine

from cradle.substrate.experiment import read_uniform_time_course_spec

#: Standard COMBINE "known format" URNs (combine-org/combine-specifications).
SBML_FORMAT = "http://identifiers.org/combine.specifications/sbml"
SEDML_FORMAT = "http://identifiers.org/combine.specifications/sed-ml"
JSON_FORMAT = "application/json"

#: The file name every curation-tier-embedding function agrees on, so a
#: consumer of *any* Cradle-produced archive knows where to look without
#: also needing the sidecar curation.json (Architecture, Layer 8: curated
#: status must survive someone copying just the .omex file elsewhere).
CURATION_TIER_ENTRY = "curation-tier.json"
DEFAULT_CURATION_TIER = "non-curated"


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


def embed_curation_tier(archive_path: str, tier: str, model_curie: str) -> None:
    """Stamp `archive_path` in place with its Cradle curation tier
    ("curated" / "non-curated") as a small JSON entry inside the archive
    itself — not only in a sidecar `curation.json` next to it, which
    wouldn't survive someone copying just the `.omex` file elsewhere.

    Rebuilds the archive from scratch (extract everything to a temp dir,
    re-`addFile` each entry plus the new one, `writeToFile`) rather than
    modifying the opened `CombineArchive` object in place and rewriting —
    that in-place pattern (`initializeFromArchive` + `addFileFromString` +
    `writeToFile`) silently zeroed out every pre-existing entry's content
    in testing, a real libcombine quirk, not a hypothetical one. Rebuilding
    from disk is exactly the same proven pattern `package_combine_archive`
    already uses, just preceded by an extraction step.
    """
    reader = libcombine.CombineArchive()
    if not reader.initializeFromArchive(archive_path):
        raise ArchiveError(f"failed to open COMBINE archive '{archive_path}'")
    master = reader.getMasterFile()
    if master is None:
        raise ArchiveError(f"COMBINE archive '{archive_path}' has no master file")
    sedml_target_name = master.getLocation()

    with tempfile.TemporaryDirectory() as tmp_dir:
        if not reader.extractTo(tmp_dir):
            raise ArchiveError(f"failed to extract '{archive_path}' before re-packaging")
        del reader  # release its handle on archive_path before overwriting it below

        sedml_path = str(Path(tmp_dir) / sedml_target_name)
        sbml_target_name = read_uniform_time_course_spec(sedml_path).model_source
        sbml_path = str(Path(tmp_dir) / sbml_target_name)

        writer = libcombine.CombineArchive()
        if not writer.addFile(sbml_path, sbml_target_name, SBML_FORMAT, False):
            raise ArchiveError("failed to re-add SBML file while embedding curation tier")
        if not writer.addFile(sedml_path, sedml_target_name, SEDML_FORMAT, True):
            raise ArchiveError("failed to re-add SED-ML file while embedding curation tier")
        payload = json.dumps({"tier": tier, "model_curie": model_curie})
        if not writer.addFileFromString(payload, CURATION_TIER_ENTRY, JSON_FORMAT, False):
            raise ArchiveError(f"failed to add curation tier entry to '{archive_path}'")
        if not writer.writeToFile(archive_path):
            raise ArchiveError(f"failed to write '{archive_path}' with curation tier embedded")


def read_curation_tier(archive_path: str) -> dict[str, str]:
    """Read the embedded curation tier, defaulting to "non-curated" per
    Layer 8's rule if an archive predates this stamp or was never promoted.
    """
    reader = libcombine.CombineArchive()
    if not reader.initializeFromArchive(archive_path):
        raise ArchiveError(f"failed to open COMBINE archive '{archive_path}'")

    entry = reader.getEntryByLocation(CURATION_TIER_ENTRY)
    if entry is None:
        return {"tier": DEFAULT_CURATION_TIER, "model_curie": ""}
    return json.loads(reader.extractEntryToString(CURATION_TIER_ENTRY))
