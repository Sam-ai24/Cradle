from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.http import get_json
from cradle.substrate.annotate import parse_curie

_MOLECULE_API = "https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
_ACTIVITY_API = (
    "https://www.ebi.ac.uk/chembl/api/data/activity.json"
    "?molecule_chembl_id={chembl_id}&standard_type=IC50&limit=25"
)


class ChEMBLConnector:
    """Bioactivity/dose-response data (Architecture, Layer 7's
    intervention-validation extension, Phase 8's drug category; CC BY-SA
    3.0, fully open per docs/RESOURCES.md).
    """

    name = "chembl"
    #: Aspirin — real, well-characterized, has real IC50 records against
    #: multiple targets.
    conformance_curie = "chembl:CHEMBL25"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "chembl"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, chembl_id = parse_curie(curie)
        molecule = get_json(_MOLECULE_API.format(chembl_id=chembl_id))
        activities = get_json(_ACTIVITY_API.format(chembl_id=chembl_id))["activities"]

        ic50_records = [
            {
                "target": a.get("target_pref_name"),
                "ic50_nm": float(a["standard_value"]),
                "assay_chembl_id": a.get("assay_chembl_id"),
            }
            for a in activities
            if a.get("standard_value") is not None and a.get("standard_units") == "nM"
        ]

        return {
            "curie": curie,
            "source": "ChEMBL",
            "license": "CC BY-SA 3.0",
            "data": {
                "chembl_id": chembl_id,
                "pref_name": molecule.get("pref_name"),
                "max_phase": molecule.get("max_phase"),
                "ic50_records": ic50_records,
            },
        }
