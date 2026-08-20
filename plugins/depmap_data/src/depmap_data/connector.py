from __future__ import annotations

import csv
import statistics

from cradle.contracts.data_connector import ConnectorRecord
from cradle.knowledge.cache import cached_download
from cradle.substrate.annotate import parse_curie

#: DepMap's public Figshare-hosted CRISPR gene-effect matrix (one row per
#: cell line, one column per gene). Pinned to a specific DepMap release's
#: file id, confirmed live as of Aug 2026 — DepMap issues a new file id
#: each release, so this will need updating for a future release rather
#: than being a permanently stable URL.
_CRISPR_GENE_EFFECT_URL = "https://ndownloader.figshare.com/files/43346616"

_LICENSE_SUMMARY = (
    "CC BY 4.0, with an explicit carve-out prohibiting use to train, develop, "
    "or enhance ML/AI models beyond internal research use (docs/RESOURCES.md, "
    "NOTICE.md) — eval/benchmark data only."
)


class DepMapConnector:
    """Genome-wide CRISPR gene-fitness-effect scores (Architecture, Layer
    7's intervention-validation extension, Phase 8's gene-fitness-screen
    category).

    Every record this connector returns carries `training_eligible: False`
    — not just a comment — so any future training pipeline built on top of
    Cradle's data layer has something to actually check before using this
    data for anything beyond evaluation, per NOTICE.md's flag on this
    source specifically.
    """

    name = "depmap"
    conformance_curie = "depmap.gene:KRAS"

    def accepts(self, curie: str) -> bool:
        namespace, _ = parse_curie(curie)
        return namespace == "depmap.gene"

    def fetch(self, curie: str) -> ConnectorRecord:
        _, gene_symbol = parse_curie(curie)
        csv_path = cached_download(_CRISPR_GENE_EFFECT_URL)

        scores: list[float] = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            column_index = next(
                (i for i, col in enumerate(header) if col.startswith(f"{gene_symbol} (")),
                None,
            )
            if column_index is None:
                raise ValueError(f"gene '{gene_symbol}' not found in DepMap CRISPRGeneEffect data")
            for row in reader:
                value = row[column_index]
                if value:
                    scores.append(float(value))

        return {
            "curie": curie,
            "source": "DepMap (Achilles CRISPR screens)",
            "license": _LICENSE_SUMMARY,
            "training_eligible": False,
            "data": {
                "gene_symbol": gene_symbol,
                "cell_line_count": len(scores),
                "mean_gene_effect": statistics.mean(scores),
                "stdev_gene_effect": statistics.stdev(scores),
                "note": (
                    "Negative gene-effect scores indicate the gene is more "
                    "essential for cell-line survival (CERES/Chronos scale, "
                    "0 = non-essential, -1 = median common essential)."
                ),
            },
        }
