from __future__ import annotations

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.gate import LicenseGate
from cradle.knowledge.http import get_text
from cradle.substrate.annotate import parse_curie

_API = "https://rest.kegg.jp/get/{entry_id}"

_LICENSE_SUMMARY = (
    "Free for individual academic use on kegg.jp only; any redistribution, "
    "caching beyond personal use, or non-academic use requires a paid "
    "license from Pathway Solutions (docs/RESOURCES.md, NOTICE.md)."
)


class KeggConnector:
    """Pathways/metabolism (Architecture, Layer 6 — a license trap, not an
    MVP source: gated by `build_gated_connector` below, off by default per
    docs/ARCHITECTURE.md).
    """

    name = "kegg"
    conformance_curie = "kegg:eco:b0345"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "kegg"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, entry_id = parse_curie(curie)
        text = get_text(_API.format(entry_id=entry_id))
        fields: dict[str, str] = {}
        for line in text.splitlines():
            if line[:1].isalpha() and len(line) > 12 and line[:12].strip():
                key = line[:12].strip()
                fields[key] = line[12:].strip()
        return {
            "curie": curie,
            "source": "KEGG",
            "license": "Restricted — see NOTICE.md",
            "data": {
                "entry": fields.get("ENTRY"),
                "symbol": fields.get("SYMBOL"),
                "name": fields.get("NAME"),
                "organism": fields.get("ORGANISM"),
            },
        }


def build_gated_connector() -> LicenseGate:
    """Entry-point factory: KEGG registers as a `LicenseGate`-wrapped
    connector, off by default (Architecture, Layer 6: "license traps to
    gate, never bake in"). Enable per-deployment via
    `CRADLE_LICENSE_ACK_KEGG=1` or by calling `.acknowledge()`.
    """
    return LicenseGate(KeggConnector(), _LICENSE_SUMMARY)
