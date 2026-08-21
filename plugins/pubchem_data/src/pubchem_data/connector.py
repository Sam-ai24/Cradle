from __future__ import annotations

import requests

from cradle.contracts.data_connector import ConnectorRecord

# PubChem's PUG REST API (https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) is a
# free, public, unauthenticated JSON API run by NCBI/NLM. No API key, no
# license gate: PubChem content is a US Government work / public domain (see
# https://pubchem.ncbi.nlm.nih.gov/docs/data-usage-policies), so unlike
# KEGG/DepMap this connector needs no `cradle.knowledge.gate.LicenseGate`.
_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_PROPERTIES = "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName"
_NAMESPACE = "pubchem.compound"


class PubChemConnector:
    """`DataConnector` for PubChem Compound records, addressed by CID.

    CURIEs use the identifiers.org namespace for PubChem compounds,
    `pubchem.compound:<CID>` (e.g. `pubchem.compound:2244` is aspirin).
    """

    name = "pubchem-data"

    # Aspirin (CID 2244) — a real, permanently-stable PubChem CID with a
    # long-published, checkable ground-truth formula/weight. Used as the
    # conformance smoke-test probe in place of the Phase 0 placeholder.
    conformance_curie = "pubchem.compound:2244"

    def fetch(self, curie: str) -> ConnectorRecord:
        cid = _parse_cid(curie)
        url = f"{_BASE_URL}/compound/cid/{cid}/property/{_PROPERTIES}/JSON"
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            raise ValueError(f"PubChem has no compound record for CID {cid} ({curie!r})")
        response.raise_for_status()
        payload = response.json()

        try:
            props = payload["PropertyTable"]["Properties"][0]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"Unexpected PubChem PUG REST response shape for {curie!r}: {payload!r}"
            ) from exc

        # PubChem PUG REST is inconsistent about how it signals "no such
        # compound": some malformed CIDs 404 or 400, but others (e.g. a
        # syntactically valid but never-assigned CID) return HTTP 200 with
        # a Properties entry that echoes only "CID" and omits every
        # property actually requested. Treat that as not-found too,
        # discovered directly against the live API rather than assumed.
        if "MolecularFormula" not in props:
            raise ValueError(f"PubChem has no compound record for CID {cid} ({curie!r})")

        return {
            "curie": curie,
            "source": "PubChem PUG REST (pubchem.ncbi.nlm.nih.gov)",
            "license": (
                "Public domain / US Government work "
                "(PubChem Data Usage Policy: "
                "https://pubchem.ncbi.nlm.nih.gov/docs/data-usage-policies)"
            ),
            "data": {
                "cid": props.get("CID"),
                "molecular_formula": props.get("MolecularFormula"),
                "molecular_weight": props.get("MolecularWeight"),
                "canonical_smiles": props.get("ConnectivitySMILES", props.get("CanonicalSMILES")),
                "iupac_name": props.get("IUPACName"),
            },
        }


def _parse_cid(curie: str) -> str:
    if ":" not in curie:
        raise ValueError(
            f"Expected a CURIE of the form '{_NAMESPACE}:<CID>', got {curie!r}"
        )
    namespace, _, local_id = curie.partition(":")
    if namespace != _NAMESPACE:
        raise ValueError(
            f"PubChemConnector only resolves '{_NAMESPACE}:...' CURIEs, got {curie!r}"
        )
    if not local_id.isdigit():
        raise ValueError(f"PubChem CID must be numeric, got {local_id!r} in {curie!r}")
    return local_id
