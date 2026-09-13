"""Runs in its own OS process, never imported into cradle-core or any other
plugin's process (Architecture, Layer 8: COBRApy is GPL/LGPL and stays
process/container-isolated, per NOTICE.md). Invoked as
`python -m cobrapy_fba.worker <sbml_path> [gene_id ...]`; prints one JSON
object to stdout. Any additional arguments name genes to knock out before
optimizing (`model.genes.get_by_id(gene_id).knock_out()`) — an additive
extension for real gene-essentiality validation (genome-scale FBA, not
the toy network): with no extra arguments this is byte-for-byte the same
behavior the adapter's existing conformance check already exercises.

Two extra commands, also additive, for the E. coli essentiality flagship
(genome-wide single-gene deletion without 1,500 model reloads):

    python -m cobrapy_fba.worker --single-gene-deletion <sbml_path>
    python -m cobrapy_fba.worker --gene-table <sbml_path>
"""

from __future__ import annotations

import json
import math
import sys


def _json_float(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _serialize_annotation(annotation: dict) -> dict:
    serialized = {}
    for key, raw in annotation.items():
        if isinstance(raw, (set, tuple, list)):
            serialized[key] = sorted(str(item) for item in raw)
        else:
            serialized[key] = raw
    return serialized


def _gene_id_from_deletion_index(index) -> str:
    if isinstance(index, (set, frozenset)):
        return str(next(iter(index)))
    text = str(index)
    if text.startswith("{") and text.endswith("}"):
        inner = text.strip("{}").strip().strip("'\"")
        return inner
    return text


def cmd_optimize(sbml_path: str, knockout_gene_ids: list[str]) -> dict:
    import cobra

    model = cobra.io.read_sbml_model(sbml_path)
    for gene_id in knockout_gene_ids:
        model.genes.get_by_id(gene_id).knock_out()
    solution = model.optimize()
    return {
        "status": solution.status,
        "objective_value": solution.objective_value,
        "fluxes": solution.fluxes.to_dict(),
    }


def cmd_gene_table(sbml_path: str) -> dict:
    import cobra

    model = cobra.io.read_sbml_model(sbml_path)
    genes = []
    for gene in model.genes:
        genes.append(
            {
                "id": gene.id,
                "name": gene.name,
                "annotation": _serialize_annotation(dict(gene.annotation)),
            }
        )
    return {
        "model_id": model.id,
        "n_genes": len(genes),
        "n_reactions": len(model.reactions),
        "n_metabolites": len(model.metabolites),
        "genes": genes,
    }


def cmd_single_gene_deletion(sbml_path: str) -> dict:
    import cobra
    from cobra.flux_analysis import single_gene_deletion

    model = cobra.io.read_sbml_model(sbml_path)
    baseline = model.optimize()
    deletions = single_gene_deletion(model, processes=1)
    genes = {}
    for index, row in deletions.iterrows():
        # cobra >= 0.29 returns a RangeIndex and puts the frozenset of
        # gene ids in an `ids` column — confirmed live against iML1515,
        # not assumed from older docs that treated the index as the id.
        raw_ids = row["ids"] if "ids" in deletions.columns else index
        gene_id = _gene_id_from_deletion_index(raw_ids)
        genes[gene_id] = {
            "growth": _json_float(row.get("growth")),
            "status": str(row.get("status")),
        }
    return {
        "model_id": model.id,
        "baseline_status": baseline.status,
        "baseline_growth": _json_float(baseline.objective_value),
        "n_genes": len(genes),
        "genes": genes,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m cobrapy_fba.worker <sbml_path> [gene_id ...]", file=sys.stderr)
        print("       python -m cobrapy_fba.worker --single-gene-deletion <sbml_path>", file=sys.stderr)
        print("       python -m cobrapy_fba.worker --gene-table <sbml_path>", file=sys.stderr)
        return 2

    if sys.argv[1] == "--single-gene-deletion":
        payload = cmd_single_gene_deletion(sys.argv[2])
    elif sys.argv[1] == "--gene-table":
        payload = cmd_gene_table(sys.argv[2])
    else:
        payload = cmd_optimize(sys.argv[1], sys.argv[2:])

    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
