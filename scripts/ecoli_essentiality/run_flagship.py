"""Run the E. coli essentiality flagship and publish artifacts.

    python scripts/ecoli_essentiality/run_flagship.py

Writes models/ecoli_flagship/{results.json,REPORT.md,essentiality.png}.
Uses only cradle.lab (plus the cobrapy plugin behind it). Live network
calls: BiGG iML1515, PEC PECData.dat, STRING v12 bulk files for taxon
511145. FBA is one subprocess (`cobra.flux_analysis.single_gene_deletion`).
"""

from __future__ import annotations

from pathlib import Path

from cradle.lab.essentiality import run_ecoli_essentiality_flagship

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "models" / "ecoli_flagship"


def main() -> int:
    result = run_ecoli_essentiality_flagship(OUTPUT_DIR)
    comparison = result["comparison"]
    fba = comparison["fba_vs_literature"]["metrics"]
    string = comparison["string_vs_literature"]
    print(f"model:           {result['model_path']}")
    print(f"results:         {result['results']}")
    print(f"report:          {result['report']}")
    print(f"figure:          {result['figure']}")
    print(f"genes:           {comparison['n_model_genes']}")
    print(f"labeled:         {comparison['n_labeled']}")
    print(f"FBA MCC:         {fba['mcc']:.3f}")
    print(f"FBA F1:          {fba['f1']:.3f}")
    print(f"STRING AUROC:    {string['auroc']}")
    print(f"STRING MCC:      {string['metrics']['mcc']:.3f}")
    print(
        "disagreements:   "
        f"FBA-only {len(comparison['disagreements']['fba_essential_literature_not'])} / "
        f"lit-only {len(comparison['disagreements']['literature_essential_fba_not'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
