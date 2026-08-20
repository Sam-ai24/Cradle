"""Runs in its own OS process, never imported into cradle-core or any other
plugin's process (Architecture, Layer 8: COBRApy is GPL/LGPL and stays
process/container-isolated, per NOTICE.md). Invoked as
`python -m cobrapy_fba.worker <sbml_path>`; prints one JSON object to stdout.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    sbml_path = sys.argv[1]

    import cobra

    model = cobra.io.read_sbml_model(sbml_path)
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
