"""Runs in its own OS process, never imported into cradle-core or any other
plugin's process (Architecture, Layer 8: COBRApy is GPL/LGPL and stays
process/container-isolated, per NOTICE.md). Invoked as
`python -m cobrapy_fba.worker <sbml_path> [gene_id ...]`; prints one JSON
object to stdout. Any additional arguments name genes to knock out before
optimizing (`model.genes.get_by_id(gene_id).knock_out()`) — an additive
extension for real gene-essentiality validation (genome-scale FBA, not
the toy network): with no extra arguments this is byte-for-byte the same
behavior the adapter's existing conformance check already exercises.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    sbml_path = sys.argv[1]
    knockout_gene_ids = sys.argv[2:]

    import cobra

    model = cobra.io.read_sbml_model(sbml_path)
    for gene_id in knockout_gene_ids:
        model.genes.get_by_id(gene_id).knock_out()
    solution = model.optimize()

    result = {
        "status": solution.status,
        "objective_value": solution.objective_value,
        "fluxes": solution.fluxes.to_dict(),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
