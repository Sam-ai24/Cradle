"""Build and execute notebooks/ecoli_essentiality.ipynb.

    python scripts/ecoli_essentiality/build_notebook.py

Reads the published models/ecoli_flagship/results.json (run
scripts/ecoli_essentiality/run_flagship.py first) so the notebook is a
lab-facing tour of a real result, not a second 1,516-LP solve. A cell
still calls cradle.lab.fba_gene_table / fetch helpers for the live
spot-checks that are cheap.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "notebooks" / "ecoli_essentiality.ipynb"


def build() -> None:
    cells = [
        new_markdown_cell(
            """# E. coli essentiality: FBA × literature × STRING

Flagship question: for genes in iML1515 (Monk et al. 2017), do flux-balance
knockouts, PEC experimental essentiality, and STRING interaction degree
agree — and when they don't, does Cradle say why?

Uses only `cradle.lab`. GEARS and DepMap are **not** the third layer:
they are human datasets. See `models/ecoli_flagship/REPORT.md`."""
        ),
        new_code_cell(
            """from pathlib import Path
from IPython.display import Image, Markdown, display
from cradle import lab

RESULTS = Path("../models/ecoli_flagship/results.json")
REPORT = Path("../models/ecoli_flagship/REPORT.md")
FIGURE = Path("../models/ecoli_flagship/essentiality.png")
print("lab essentiality entry points:", [name for name in dir(lab) if "essential" in name.lower() or name.startswith("fba_") or name.startswith("fetch_")])
print("results exist:", RESULTS.exists())"""
        ),
        new_markdown_cell(
            """## 1. Load the published comparison

`scripts/ecoli_essentiality/run_flagship.py` already ran genome-wide
single-gene deletion (one COBRApy subprocess), PEC `PECData.dat`, and
STRING v12 taxon 511145. Re-solving 1,516 LPs inside the notebook would
not change the science."""
        ),
        new_code_cell(
            """import json
payload = json.loads(RESULTS.read_text())
cmp = payload["comparison"]
print("model:", payload["model_curie"])
print("WT growth /h:", round(cmp["baseline_growth"], 4))
print("genes:", cmp["n_model_genes"], "UniProt-labeled:", cmp["n_labeled"])
print("FBA vs UniProt:", cmp["fba_vs_literature"]["metrics"])
print("STRING vs PEC AUROC:", cmp["string_vs_literature"]["auroc"])
print("STRING vs PEC MCC:", cmp["string_vs_literature"]["metrics"]["mcc"])"""
        ),
        new_markdown_cell("## 2. Known-gene spot checks, including folA/folM"),
        new_code_cell(
            """for item in cmp["known_genes"]:
    obs = item["observed"] or {}
    print(
        f"{item['name']:5} {item['id']}  "
        f"FBA expected={item['fba_expected']:13} observed_essential={obs.get('fba_essential')}  "
        f"lit expected={item['literature_essential']} observed={obs.get('literature_essential')}  "
        f"growth={obs.get('fba_growth')}"
    )"""
        ),
        new_markdown_cell(
            """## 3. Cheap live checks

The cobrapy adapter still answers individual knockouts the way
`tests/test_genome_scale_fba.py` does."""
        ),
        new_code_cell(
            """wt = lab.fba_knockout([])["objective_value"]
murA = lab.fba_knockout(["b3189"])["objective_value"]
folA = lab.fba_knockout(["b0048"])["objective_value"]
print(f"WT={wt:.4f}  murA KO={murA:.4e}  folA KO={folA:.4f}")
assert murA < 1e-6
assert abs(folA - wt) < 1e-6"""
        ),
        new_markdown_cell("## 4. Figure and report"),
        new_code_cell(
            """display(Image(filename=str(FIGURE)))
display(Markdown(REPORT.read_text().split("## Disagreements")[0]))
print("FBA-only disagreements:", len(cmp["disagreements"]["fba_essential_literature_not"]))
print("literature-only disagreements:", len(cmp["disagreements"]["literature_essential_fba_not"]))
print("first five literature-only (includes folA if UniProt agrees):")
for row in cmp["disagreements"]["literature_essential_fba_not"][:5]:
    print(" ", row)"""
        ),
    ]
    notebook = new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(OUTPUT_PATH.parent)}},
    )
    client.execute()
    OUTPUT_PATH.write_text(nbformat.writes(notebook), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
