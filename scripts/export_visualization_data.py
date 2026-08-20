"""Phase 10: export real Cradle data into the static JSON/structure files
the local visualization page reads. Run once, from the repo root, with
Phase 1/2/3 dependencies installed:

    python scripts/export_visualization_data.py

Writes viz/data/repressilator_graph.json, viz/data/repressilator_trajectories.json,
and viz/data/structures/<accession>.pdb — real structure files downloaded
once here (server-side, no CORS concerns) rather than fetched live by the
browser from alphafold.ebi.ac.uk, which has no CORS headers and would
likely fail a live cross-origin fetch. Not part of the installed `cradle`
package - a one-time data-preparation step, like curate_repressilator.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import libsbml  # noqa: E402

from cradle.knowledge.http import HttpError, get_json, get_text  # noqa: E402
from cradle.registry import discover  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = REPO_ROOT / "models" / "repressilator" / "repressilator.xml"
ARCHIVE_PATH = REPO_ROOT / "models" / "repressilator" / "repressilator.omex"
OUTPUT_DIR = REPO_ROOT / "viz" / "data"
STRUCTURES_DIR = OUTPUT_DIR / "structures"

#: The real regulatory logic, quoted directly from the model's own SBML
#: notes (models/repressilator/repressilator.xml) rather than asserted:
#: "LacI ... inhibits ... tetR ... Protein tetR inhibits the gene CI from
#: phage Lambda ... protein CI inhibits lacI expression."
REPRESSION_RING = [("PX", "PY"), ("PY", "PZ"), ("PZ", "PX")]


def export_graph() -> dict:
    document = libsbml.readSBMLFromFile(str(MODEL_PATH))
    model = document.getModel()

    nodes = []
    accession_by_species = {}
    for species_id in ("PX", "PY", "PZ"):
        species = model.getSpecies(species_id)
        curie = None
        if species.getNumCVTerms() > 0:
            uri = species.getCVTerm(0).getResourceURI(0)
            curie = uri.replace("http://identifiers.org/", "").replace("/", ":")
            accession_by_species[species_id] = curie.split(":")[1]
        nodes.append(
            {
                "data": {
                    "id": species_id,
                    "label": species.getName(),
                    "curie": curie,
                }
            }
        )

    edges = [
        {"data": {"source": src, "target": dst, "label": "represses"}}
        for src, dst in REPRESSION_RING
    ]

    return {"elements": {"nodes": nodes, "edges": edges}}, accession_by_species


def download_structures(accession_by_species: dict[str, str]) -> dict:
    STRUCTURES_DIR.mkdir(parents=True, exist_ok=True)
    structure_by_species = {}
    for species_id, accession in accession_by_species.items():
        try:
            prediction = get_json(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}")[0]
        except HttpError as exc:
            # A real, expected gap, not a bug: AlphaFold DB covers most but
            # not all of UniProt (confirmed here for P03034, the
            # bacteriophage lambda CI repressor - genuinely absent, not a
            # transient failure). Skip gracefully rather than crash the
            # whole export over one missing structure.
            print(f"No AlphaFold DB entry for {species_id} ({accession}): {exc}")
            continue

        pdb_url = prediction["pdbUrl"]
        local_path = STRUCTURES_DIR / f"{accession}.pdb"
        if not local_path.exists():
            print(f"Downloading real AlphaFold structure for {species_id} ({accession})...")
            local_path.write_text(get_text(pdb_url), encoding="utf-8")

        structure_by_species[species_id] = {
            "accession": accession,
            "local_path": f"data/structures/{accession}.pdb",
            "global_plddt": prediction.get("globalMetricValue"),
        }
    return structure_by_species


def export_trajectories() -> dict:
    print("Running the published repressilator archive on Tellurium and COPASI...")
    trajectories = {}
    for entry_point_name in ("tellurium", "copasi"):
        for plugin in discover("simulation_adapter"):
            if plugin.entry_point_name == entry_point_name:
                result = plugin.instance.run({"combine_archive": str(ARCHIVE_PATH)}, {})
                trajectories[entry_point_name] = {
                    "t": result["t"],
                    "PX": result["trajectories"]["PX"],
                }
    return trajectories


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    graph, accession_by_species = export_graph()
    structures = download_structures(accession_by_species)
    for node in graph["elements"]["nodes"]:
        species_id = node["data"]["id"]
        if species_id in structures:
            node["data"]["structure"] = structures[species_id]

    (OUTPUT_DIR / "repressilator_graph.json").write_text(json.dumps(graph, indent=2))

    trajectories = export_trajectories()
    (OUTPUT_DIR / "repressilator_trajectories.json").write_text(json.dumps(trajectories, indent=2))

    print(f"\nWrote {OUTPUT_DIR / 'repressilator_graph.json'}")
    print(f"Wrote {OUTPUT_DIR / 'repressilator_trajectories.json'}")
    print(f"Downloaded {len(structures)} real structure files to {STRUCTURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
