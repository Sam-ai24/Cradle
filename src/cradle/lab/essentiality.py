"""E. coli gene essentiality across FBA, literature, and a network baseline.

Flagship question: for genes in iML1515 (Monk et al. 2017), do flux-balance
knockouts, PEC experimental essentiality, and STRING interaction degree
agree — and when they don't, does Cradle's provenance say why?

This is deliberately *not* GEARS or DepMap. GEARS is trained on Norman
et al. 2019 human K562 Perturb-seq; DepMap Achilles is human cancer-line
fitness. Using either as an E. coli essentiality predictor would be a
wrong-organism result dressed up as a third layer. STRING taxon 511145
(E. coli K-12 MG1655) is the same strain as iML1515; UniProt organism
83333 is E. coli K-12. Those are organism-matched.

Media confounder, stated up front rather than cleaned up: iML1515's
default FBA condition is aerobic glucose minimal medium; PEC classifies
genes as essential / non-essential from knockout viability (Keio-class
rich-media genetics), not a glucose-M9 screen. Disagreements are
therefore a mixture of model error, isozyme annotation (see folA/folM),
and that media mismatch. The comparison still has to beat a naive
baseline (STRING degree, Jeong et al. 2001 hub-essentiality) to be worth
reporting.

UniProt keyword KW-0256 ("Essential protein") was tried first as a
Cradle-native connector query and returned **zero** reviewed E. coli
K-12 entries — confirmed live 2026-09-13, not assumed. PEC's published
`PECData.dat` is the literature layer instead.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

from cradle.knowledge.cache import cached_download
from cradle.knowledge.http import get_text
from cradle.lab.api import LabError
from cradle.registry import discover

IML1515_URL = "http://bigg.ucsd.edu/static/models/iML1515.xml"
IML1515_CURIE = "bigg.model:iML1515"
UNIPROT_STREAM = "https://rest.uniprot.org/uniprotkb/stream"
PEC_DATA_URL = "https://shigen.nig.ac.jp/ecoli/pec/download/files/PECData.dat"
STRING_LINKS_URL = (
    "https://stringdb-downloads.org/download/protein.links.v12.0/"
    "511145.protein.links.v12.0.txt.gz"
)
STRING_INFO_URL = (
    "https://stringdb-downloads.org/download/protein.info.v12.0/"
    "511145.protein.info.v12.0.txt.gz"
)
ECOLI_TAXON = 511145
UNIPROT_ORGANISM_ID = 83333
STRING_SCORE_CUTOFF = 700
FBA_ESSENTIAL_FRACTION = 0.01
_BNUMBER_RE = re.compile(r"\bb\d{4}\b", re.IGNORECASE)

# Spot-checks used as live assertions, not as the dataset. b-numbers were
# looked up from iML1515 itself in tests/test_genome_scale_fba.py.
KNOWN = {
    "murA": {"id": "b3189", "literature_essential": True, "fba_expected": "essential"},
    "accA": {"id": "b0185", "literature_essential": True, "fba_expected": "essential"},
    "lacZ": {"id": "b0344", "literature_essential": False, "fba_expected": "nonessential"},
    "lacY": {"id": "b0343", "literature_essential": False, "fba_expected": "nonessential"},
    "araA": {"id": "b0062", "literature_essential": False, "fba_expected": "nonessential"},
    "folA": {"id": "b0048", "literature_essential": True, "fba_expected": "nonessential"},
}


def _cobrapy_adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "cobrapy":
            return plugin.instance
    raise LabError(
        "compare_ecoli_essentiality requires the cobrapy plugin: "
        "pip install -e plugins/cobrapy_fba"
    )


def download_iml1515() -> Path:
    """Fetch iML1515 from BiGG (cached under ~/.cradle/cache)."""
    return cached_download(IML1515_URL)


def fba_gene_table(sbml_path: str | Path | None = None) -> dict[str, Any]:
    path = str(sbml_path or download_iml1515())
    return _cobrapy_adapter().gene_table(path)


def fba_single_gene_deletion(sbml_path: str | Path | None = None) -> dict[str, Any]:
    path = str(sbml_path or download_iml1515())
    return _cobrapy_adapter().single_gene_deletion(path)


def fba_knockout(gene_ids: list[str], sbml_path: str | Path | None = None) -> dict[str, Any]:
    """One FBA solve with the named genes knocked out. Returns status + growth."""
    path = str(sbml_path or download_iml1515())
    result = _cobrapy_adapter().run({"sbml_path": path}, {"gene_knockouts": gene_ids})
    return {
        "status": result.get("status"),
        "objective_value": result.get("objective_value"),
        "engine": result.get("engine"),
    }


def classify_fba_growth(
    growth: float | None,
    baseline: float,
    fraction: float = FBA_ESSENTIAL_FRACTION,
) -> str:
    """Essential if the knockout growth rate is below `fraction` of WT.

    Matches the COBRA community's usual 1% cutoff, not the stricter
    ~0.0 used for the two textbook-lethal genes in
    tests/test_genome_scale_fba.py (those still classify as essential
    here). A missing/NaN growth is treated as lethal.
    """
    if baseline <= 0:
        raise LabError(f"baseline growth must be positive, got {baseline}")
    if growth is None or growth < fraction * baseline:
        return "essential"
    return "nonessential"


def _parse_bnumbers(*texts: str | None) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in _BNUMBER_RE.findall(text):
            b_number = match.lower()
            if b_number not in seen:
                seen.add(b_number)
                found.append(b_number)
    return found


def _uniprot_stream(query: str, fields: str) -> str:
    url = UNIPROT_STREAM + "?" + urlencode(
        {"query": query, "fields": fields, "format": "tsv"}
    )
    return get_text(url, timeout=120.0)


def fetch_uniprot_essentiality() -> dict[str, Any]:
    """Deprecated name kept so notebooks that already imported it still run.

    UniProt KW-0256 is empty for E. coli K-12; this now returns PEC.
    """
    return fetch_pec_essentiality()


def fetch_pec_essentiality() -> dict[str, Any]:
    """Literature layer: PEC (Profiling of E. coli Chromosome) gene classes.

    Class 1 = essential, 2 = non-essential, 3 = unknown. Unknown is left
    unlabeled rather than forced into a binary. Source file is the public
    PEC download (`PECData.dat`), fetched live and cached.
    """
    path = cached_download(PEC_DATA_URL, timeout=120.0)
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    class_key = "Class(1:essential 2:noessential 3:unknown)"
    labels: dict[str, dict[str, Any]] = {}
    n_essential = n_nonessential = n_unknown = 0
    for row in rows:
        klass = (row.get(class_key) or "").strip()
        names = " ".join(
            [
                row.get("Orf") or "",
                row.get("Alternative name") or "",
            ]
        )
        b_numbers = _parse_bnumbers(names)
        if klass == "1":
            n_essential += 1
            flag: bool | None = True
        elif klass == "2":
            n_nonessential += 1
            flag = False
        else:
            n_unknown += 1
            flag = None
        for b_number in b_numbers:
            labels[b_number] = {
                "literature_essential": flag,
                "pec_class": klass,
                "orf": row.get("Orf") or "",
                "product": row.get("Product") or "",
                "uniprot": None,
                "curie": None,
                "gene_primary": row.get("Orf") or "",
            }

    labeled = {k: v for k, v in labels.items() if v["literature_essential"] is not None}
    return {
        "source": "PEC (Profiling of E. coli Chromosome)",
        "license": "public download from NIG Japan; cite Kato & Hashimoto 2007, PMID 18000006, and Baba et al. 2006 for the underlying Keio genetics",
        "url": PEC_DATA_URL,
        "n_rows": len(rows),
        "n_class_essential": n_essential,
        "n_class_nonessential": n_nonessential,
        "n_class_unknown": n_unknown,
        "n_bnumbers_labeled": len(labeled),
        "n_bnumbers_essential": sum(1 for item in labeled.values() if item["literature_essential"]),
        "labels": labels,
        "caveat": (
            "PEC class is knockout-viability / Keio-class genetics (rich media), "
            "not a glucose-M9 screen. iML1515 FBA is aerobic glucose minimal. "
            "UniProt KW-0256 returned zero reviewed E. coli K-12 entries "
            "(checked live 2026-09-13), so PEC is the literature layer."
        ),
    }


def _read_gzip_text(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def fetch_string_degrees(
    score_cutoff: int = STRING_SCORE_CUTOFF,
) -> dict[str, Any]:
    """Perturbation/network baseline: STRING v12 degree in taxon 511145.

    High-confidence edges only (combined_score >= 700). Degree is a
    scalar_phenotype-style score: more partners → more likely essential,
    the Jeong et al. 2001 hub result, used here as the field's simplest
    network baseline the way Phase 12 used PCA against Geneformer.

    The registered `string` DataConnector defaults to human (NCBI 9606) —
    confirmed in plugins/string_data, not assumed — so this flagship
    does not call it 1,516 times. It uses STRING's own bulk files for
    E. coli K-12 MG1655 instead.
    """
    links_path = cached_download(STRING_LINKS_URL, timeout=180.0)
    info_path = cached_download(STRING_INFO_URL, timeout=180.0)
    info_text = _read_gzip_text(info_path)
    links_text = _read_gzip_text(links_path)

    info_reader = csv.DictReader(io.StringIO(info_text), delimiter="\t")
    id_to_name: dict[str, str] = {}
    name_to_id: dict[str, str] = {}
    b_to_id: dict[str, str] = {}
    for row in info_reader:
        string_id = (row.get("#string_protein_id") or row.get("string_protein_id") or "").strip()
        preferred = (row.get("preferred_name") or "").strip()
        if not string_id:
            continue
        id_to_name[string_id] = preferred
        if preferred:
            name_to_id[preferred.lower()] = string_id
        for b_number in _parse_bnumbers(string_id, preferred):
            b_to_id[b_number] = string_id

    degree: dict[str, int] = {string_id: 0 for string_id in id_to_name}
    n_edges = 0
    for line in links_text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        protein_a, protein_b, score_s = parts[0], parts[1], parts[2]
        try:
            score = int(score_s)
        except ValueError:
            continue
        if score < score_cutoff:
            continue
        if protein_a in degree:
            degree[protein_a] += 1
        if protein_b in degree:
            degree[protein_b] += 1
        n_edges += 1

    by_bnumber: dict[str, dict[str, Any]] = {}
    for b_number, string_id in b_to_id.items():
        by_bnumber[b_number] = {
            "string_id": string_id,
            "preferred_name": id_to_name.get(string_id, ""),
            "degree": degree.get(string_id, 0),
        }

    return {
        "source": "STRING v12.0",
        "license": "CC BY 4.0",
        "taxon": ECOLI_TAXON,
        "score_cutoff": score_cutoff,
        "n_proteins": len(id_to_name),
        "n_edges_kept": n_edges,
        "links_url": STRING_LINKS_URL,
        "info_url": STRING_INFO_URL,
        "by_bnumber": by_bnumber,
        "name_to_id": name_to_id,
        "degree_by_id": degree,
        "id_to_name": id_to_name,
        "caveat": (
            "The registered string DataConnector defaults to human (9606). "
            "This baseline uses STRING bulk files for taxon 511145 instead."
        ),
    }


def confusion_counts(pairs: Iterable[tuple[bool, bool]]) -> dict[str, int]:
    """pairs are (predicted_essential, literature_essential)."""
    tp = fp = tn = fn = 0
    for predicted, literature in pairs:
        if predicted and literature:
            tp += 1
        elif predicted and not literature:
            fp += 1
        elif (not predicted) and (not literature):
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def binary_metrics(counts: dict[str, int]) -> dict[str, float]:
    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )
    accuracy = (tp + tn) / total if total else 0.0
    # Matthews correlation: 0 if any factor is zero.
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / denom if denom else 0.0
    return {
        "n": float(total),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "mcc": mcc,
    }


def auroc(scores: list[float], labels: list[bool]) -> float | None:
    """Mann-Whitney AUROC. None if either class is empty."""
    positive = [score for score, label in zip(scores, labels) if label]
    negative = [score for score, label in zip(scores, labels) if not label]
    if not positive or not negative:
        return None
    wins = 0.0
    for pos in positive:
        for neg in negative:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def _uniprot_from_annotation(annotation: dict[str, Any]) -> str | None:
    raw = annotation.get("uniprot") or annotation.get("uniprot.uniprot")
    if not raw:
        return None
    if isinstance(raw, list):
        return str(raw[0]) if raw else None
    return str(raw)


def compare_essentiality(
    deletion: dict[str, Any],
    gene_table: dict[str, Any],
    literature: dict[str, Any],
    string_degrees: dict[str, Any],
    *,
    fraction: float = FBA_ESSENTIAL_FRACTION,
) -> dict[str, Any]:
    """Join the three layers on iML1515 b-numbers and score them."""
    baseline = deletion["baseline_growth"]
    labels = literature["labels"]
    string_by_b = string_degrees["by_bnumber"]
    name_to_id = string_degrees["name_to_id"]
    degree_by_id = string_degrees["degree_by_id"]

    genes_meta = {gene["id"]: gene for gene in gene_table["genes"]}
    rows: list[dict[str, Any]] = []

    for gene_id, knockout in deletion["genes"].items():
        meta = genes_meta.get(gene_id, {"id": gene_id, "name": "", "annotation": {}})
        name = (meta.get("name") or "").strip()
        annotation = meta.get("annotation") or {}
        lit = labels.get(gene_id.lower())
        string_hit = string_by_b.get(gene_id.lower())
        if string_hit is None and name:
            string_id = name_to_id.get(name.lower())
            if string_id:
                string_hit = {
                    "string_id": string_id,
                    "preferred_name": name,
                    "degree": degree_by_id.get(string_id, 0),
                }
        fba_class = classify_fba_growth(knockout.get("growth"), baseline, fraction)
        uniprot_acc = _uniprot_from_annotation(annotation)
        if uniprot_acc is None and lit:
            uniprot_acc = lit.get("uniprot") or None
        row = {
            "gene_id": gene_id,
            "name": name,
            "fba_growth": knockout.get("growth"),
            "fba_status": knockout.get("status"),
            "fba_essential": fba_class == "essential",
            "literature_essential": None if lit is None else bool(lit["literature_essential"]),
            "uniprot": uniprot_acc,
            "curie": f"uniprot:{uniprot_acc}" if uniprot_acc else None,
            "string_id": None if string_hit is None else string_hit["string_id"],
            "string_degree": None if string_hit is None else int(string_hit["degree"]),
        }
        rows.append(row)

    labeled = [row for row in rows if row["literature_essential"] is not None]
    fba_pairs = [
        (row["fba_essential"], row["literature_essential"]) for row in labeled
    ]
    fba_counts = confusion_counts(fba_pairs)
    fba_metrics = binary_metrics(fba_counts)

    degree_rows = [
        row
        for row in labeled
        if row["string_degree"] is not None
    ]
    string_auroc = auroc(
        [float(row["string_degree"]) for row in degree_rows],
        [bool(row["literature_essential"]) for row in degree_rows],
    )
    # Invert growth so essential (low/zero growth) scores higher for AUROC.
    fba_auroc = auroc(
        [
            0.0 if row["fba_growth"] is None else -float(row["fba_growth"])
            for row in labeled
        ],
        [bool(row["literature_essential"]) for row in labeled],
    )

    # Naive STRING classifier: essential if degree >= median of labeled set.
    degrees_labeled = sorted(float(row["string_degree"]) for row in degree_rows)
    median_degree = (
        degrees_labeled[len(degrees_labeled) // 2] if degrees_labeled else 0.0
    )
    string_pairs = [
        (float(row["string_degree"]) >= median_degree, bool(row["literature_essential"]))
        for row in degree_rows
    ]
    string_counts = confusion_counts(string_pairs)
    string_metrics = binary_metrics(string_counts)

    fba_only = [
        {"gene_id": row["gene_id"], "name": row["name"], "fba_growth": row["fba_growth"]}
        for row in labeled
        if row["fba_essential"] and not row["literature_essential"]
    ]
    lit_only = [
        {"gene_id": row["gene_id"], "name": row["name"], "fba_growth": row["fba_growth"]}
        for row in labeled
        if (not row["fba_essential"]) and row["literature_essential"]
    ]

    known_rows = []
    for name, spec in KNOWN.items():
        match = next((row for row in rows if row["gene_id"] == spec["id"]), None)
        known_rows.append({"name": name, **spec, "observed": match})

    return {
        "model_curie": IML1515_CURIE,
        "baseline_growth": baseline,
        "fba_essential_fraction": fraction,
        "n_model_genes": len(rows),
        "n_labeled": len(labeled),
        "n_fba_essential": sum(1 for row in rows if row["fba_essential"]),
        "n_literature_essential_in_model": sum(
            1 for row in labeled if row["literature_essential"]
        ),
        "fba_vs_literature": {"counts": fba_counts, "metrics": fba_metrics, "auroc": fba_auroc},
        "string_vs_literature": {
            "counts": string_counts,
            "metrics": string_metrics,
            "auroc": string_auroc,
            "median_degree_threshold": median_degree,
            "n_with_degree": len(degree_rows),
        },
        "disagreements": {
            "fba_essential_literature_not": fba_only,
            "literature_essential_fba_not": lit_only,
        },
        "known_genes": known_rows,
        "rows": rows,
    }


def plot_essentiality(comparison: dict[str, Any], output_path: str | Path) -> Path:
    """Two-panel figure: FBA vs literature confusion, STRING AUROC-style boxes."""
    import matplotlib.pyplot as plt

    labeled = [
        row for row in comparison["rows"] if row["literature_essential"] is not None
    ]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))

    counts = comparison["fba_vs_literature"]["counts"]
    matrix = [
        [counts["tp"], counts["fp"]],
        [counts["fn"], counts["tn"]],
    ]
    axes[0].imshow(matrix, cmap="Blues")
    axes[0].set_xticks([0, 1], ["lit essential", "lit not"])
    axes[0].set_yticks([0, 1], ["FBA essential", "FBA not"])
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, str(matrix[i][j]), ha="center", va="center", color="black")
    metrics = comparison["fba_vs_literature"]["metrics"]
    axes[0].set_title(
        f"FBA vs PEC  MCC={metrics['mcc']:.2f}  F1={metrics['f1']:.2f}"
    )

    ess_deg = [
        row["string_degree"]
        for row in labeled
        if row["string_degree"] is not None and row["literature_essential"]
    ]
    non_deg = [
        row["string_degree"]
        for row in labeled
        if row["string_degree"] is not None and not row["literature_essential"]
    ]
    axes[1].boxplot([non_deg, ess_deg], showfliers=False)
    axes[1].set_xticklabels(["lit not essential", "lit essential"])
    auroc_value = comparison["string_vs_literature"]["auroc"]
    auroc_text = "NA" if auroc_value is None else f"{auroc_value:.2f}"
    axes[1].set_ylabel("STRING degree (score ≥ 700)")
    axes[1].set_title(f"STRING hub baseline  AUROC={auroc_text}")

    fig.suptitle("E. coli iML1515 essentiality: FBA × PEC × STRING")
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return output


def write_essentiality_report(
    comparison: dict[str, Any],
    literature: dict[str, Any],
    string_degrees: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Markdown lab report for the flagship comparison."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fba = comparison["fba_vs_literature"]
    strg = comparison["string_vs_literature"]
    known_lines = []
    for item in comparison["known_genes"]:
        observed = item.get("observed") or {}
        known_lines.append(
            f"| {item['name']} | `{item['id']}` | {item['fba_expected']} | "
            f"{observed.get('fba_essential')} | {item['literature_essential']} | "
            f"{observed.get('literature_essential')} | {observed.get('fba_growth')} |"
        )
    fba_only = comparison["disagreements"]["fba_essential_literature_not"][:15]
    lit_only = comparison["disagreements"]["literature_essential_fba_not"][:15]

    def _fmt_metrics(block: dict[str, Any]) -> str:
        m = block["metrics"]
        auroc_value = block.get("auroc")
        auroc_text = "NA" if auroc_value is None else f"{auroc_value:.3f}"
        return (
            f"- n={int(m['n'])}  precision={m['precision']:.3f}  "
            f"recall={m['recall']:.3f}  F1={m['f1']:.3f}  "
            f"accuracy={m['accuracy']:.3f}  MCC={m['mcc']:.3f}  AUROC={auroc_text}"
        )

    body = f"""# E. coli essentiality: FBA × PEC × STRING

- **Model:** `{comparison['model_curie']}` (Monk et al. 2017, PMID 29020004)
- **Generated:** {datetime.now(timezone.utc).isoformat()}
- **FBA condition:** iML1515 default (aerobic glucose minimal), WT growth {comparison['baseline_growth']:.4f} /h
- **FBA essential cutoff:** growth < {comparison['fba_essential_fraction']} × WT
- **Literature:** {literature['source']} — {literature['caveat']}
- **Network baseline:** {string_degrees['source']} taxon {string_degrees['taxon']}, combined_score ≥ {string_degrees['score_cutoff']} — {string_degrees['caveat']}

## Why GEARS / DepMap are not the third layer

GEARS is trained on Norman et al. 2019 **human K562** Perturb-seq.
DepMap Achilles is **human cancer-line** fitness and is license-gated against
AI-training use. Neither is an E. coli essentiality predictor. STRING
taxon 511145 is the same strain as iML1515.

## Counts

- iML1515 genes: {comparison['n_model_genes']}
- PEC-labeled genes in the model: {comparison['n_labeled']}
- FBA-essential: {comparison['n_fba_essential']}
- PEC-essential in the model: {comparison['n_literature_essential_in_model']}

## FBA vs PEC

{_fmt_metrics(fba)}

Confusion: TP={fba['counts']['tp']} FP={fba['counts']['fp']} TN={fba['counts']['tn']} FN={fba['counts']['fn']}

## STRING degree vs PEC

{_fmt_metrics(strg)}

Median-degree threshold used only for the binary scores: {strg['median_degree_threshold']}

## Known-gene spot checks

| gene | b-number | FBA expected | FBA observed essential | lit expected | lit observed | FBA growth |
|---|---|---|---|---|---|---|
{chr(10).join(known_lines)}

`folA` (b0048) is the documented isozyme rescue: literature-essential DHFR,
non-lethal in iML1515 because the GPR is `b1606 or b0048` (`folM`).

## Disagreements (first 15 each)

FBA essential, PEC not ({len(comparison['disagreements']['fba_essential_literature_not'])} total):
{chr(10).join(f"- `{row['gene_id']}` {row['name']} growth={row['fba_growth']}" for row in fba_only) or "- none"}

PEC essential, FBA not ({len(comparison['disagreements']['literature_essential_fba_not'])} total):
{chr(10).join(f"- `{row['gene_id']}` {row['name']} growth={row['fba_growth']}" for row in lit_only) or "- none"}
"""
    output.write_text(body, encoding="utf-8")
    return output


def write_results_json(payload: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    return output


def run_ecoli_essentiality_flagship(
    output_dir: str | Path,
    *,
    sbml_path: str | Path | None = None,
) -> dict[str, Any]:
    """End-to-end flagship: download, FBA deletions, PEC, STRING, join."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = Path(sbml_path) if sbml_path else download_iml1515()
    gene_table = fba_gene_table(model_path)
    deletion = fba_single_gene_deletion(model_path)
    literature = fetch_pec_essentiality()
    string_degrees = fetch_string_degrees()
    comparison = compare_essentiality(deletion, gene_table, literature, string_degrees)
    figure = plot_essentiality(comparison, out / "essentiality.png")
    report = write_essentiality_report(
        comparison, literature, string_degrees, out / "REPORT.md"
    )
    # Published JSON drops the bulky per-gene rows' redundancy by keeping them;
    # they *are* the result. STRING name maps stay out.
    published = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_curie": IML1515_CURIE,
        "model_url": IML1515_URL,
        "literature": {k: v for k, v in literature.items() if k != "labels"},
        "string": {
            k: v
            for k, v in string_degrees.items()
            if k not in {"name_to_id", "degree_by_id", "id_to_name", "by_bnumber"}
        },
        "comparison": comparison,
    }
    results = write_results_json(published, out / "results.json")
    return {
        "model_path": str(model_path),
        "figure": str(figure),
        "report": str(report),
        "results": str(results),
        "comparison": comparison,
        "literature": literature,
        "string": string_degrees,
    }
