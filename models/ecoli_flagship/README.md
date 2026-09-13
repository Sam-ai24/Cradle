# E. coli essentiality flagship

One biological question, three Cradle layers, on the same genes:

| Layer | What | Organism match |
|---|---|---|
| Mechanistic perturbation | iML1515 FBA single-gene deletion (glucose minimal, aerobic) | *E. coli* K-12 MG1655 |
| Literature | PEC `PECData.dat` essential / non-essential classes | same strain |
| Network baseline | STRING v12 degree, taxon 511145, score ≥ 700 | same strain |

GEARS (human K562 Perturb-seq) and DepMap (human cancer lines) are **not** used here. That is a scientific choice, not a missing plugin.

## How to regenerate

```bash
pip install -e ".[dev,lab]" -e plugins/cobrapy_fba
python scripts/ecoli_essentiality/run_flagship.py
```

Live fetches: BiGG iML1515, PEC, STRING bulk files (cached under `~/.cradle/cache`). FBA is one COBRApy subprocess.

## Published artifacts

- `results.json` — per-gene table + confusion metrics
- `REPORT.md` — human-readable lab report
- `essentiality.png` — confusion matrix + STRING boxplot
- `../notebooks/ecoli_essentiality.ipynb` — executed notebook over this result

See `REPORT.md` for the numbers. Headline: FBA MCC against PEC is ~0.57 (AUROC ~0.87); STRING degree MCC is ~0.11 (AUROC ~0.63). `folA` is PEC-essential and FBA-nonessential because iML1515's own GPR is `folA or folM`.
