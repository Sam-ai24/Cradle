# E. coli essentiality: FBA × PEC × STRING

- **Model:** `bigg.model:iML1515` (Monk et al. 2017, PMID 29020004)
- **Generated:** 2026-09-13T10:53:10.958193+00:00
- **FBA condition:** iML1515 default (aerobic glucose minimal), WT growth 0.8770 /h
- **FBA essential cutoff:** growth < 0.01 × WT
- **Literature:** PEC (Profiling of E. coli Chromosome) — PEC class is knockout-viability / Keio-class genetics (rich media), not a glucose-M9 screen. iML1515 FBA is aerobic glucose minimal. UniProt KW-0256 returned zero reviewed E. coli K-12 entries (checked live 2026-09-13), so PEC is the literature layer.
- **Network baseline:** STRING v12.0 taxon 511145, combined_score ≥ 700 — The registered string DataConnector defaults to human (9606). This baseline uses STRING bulk files for taxon 511145 instead.

## Why GEARS / DepMap are not the third layer

GEARS is trained on Norman et al. 2019 **human K562** Perturb-seq.
DepMap Achilles is **human cancer-line** fitness and is license-gated against
AI-training use. Neither is an E. coli essentiality predictor. STRING
taxon 511145 is the same strain as iML1515.

## Counts

- iML1515 genes: 1516
- PEC-labeled genes in the model: 1515
- FBA-essential: 196
- PEC-essential in the model: 119

## FBA vs PEC

- n=1515  precision=0.477  recall=0.782  F1=0.592  accuracy=0.916  MCC=0.569  AUROC=0.867

Confusion: TP=93 FP=102 TN=1294 FN=26

## STRING degree vs PEC

- n=1513  precision=0.106  recall=0.714  F1=0.184  accuracy=0.503  MCC=0.107  AUROC=0.633

Median-degree threshold used only for the binary scores: 30.0

## Known-gene spot checks

| gene | b-number | FBA expected | FBA observed essential | lit expected | lit observed | FBA growth |
|---|---|---|---|---|---|---|
| murA | `b3189` | essential | True | True | True | 2.9044203843129533e-16 |
| accA | `b0185` | essential | True | True | True | -1.2023677115050504e-15 |
| lacZ | `b0344` | nonessential | False | False | False | 0.8769972144269803 |
| lacY | `b0343` | nonessential | False | False | False | 0.8769972144269774 |
| araA | `b0062` | nonessential | False | False | False | 0.8769972144269822 |
| folA | `b0048` | nonessential | False | True | True | 0.8769972144269593 |

`folA` (b0048) is the documented isozyme rescue: literature-essential DHFR,
non-lethal in iML1515 because the GPR is `b1606 or b0048` (`folM`).

## Disagreements (first 15 each)

FBA essential, PEC not (102 total):
- `b2564` pdxJ growth=1.5611268556990072e-16
- `b3770` ilvE growth=-7.499116637562349e-16
- `b2499` purM growth=4.299717659933334e-14
- `b1693` aroD growth=0.0
- `b3177` folP growth=0.0
- `b0778` bioD growth=0.0
- `b2600` tyrA growth=1.141106972992096e-17
- `b0004` thrC growth=4.5774483070637465e-17
- `b0133` panC growth=3.5550992108073615e-12
- `b0777` bioC growth=0.0
- `b3991` thiG growth=-2.0795129529483956e-15
- `b2476` purC growth=9.389563157184872e-14
- `b0523` purE growth=-1.8230209681787005e-14
- `b3958` argC growth=-9.869254654355428e-16
- `b2020` hisD growth=-7.200459433083986e-16

PEC essential, FBA not (26 total):
- `b3640` dut growth=0.8769972144269726
- `b2234` nrdA growth=0.8769972144269919
- `b0171` pyrH growth=0.8769972144269802
- `b0954` fabA growth=0.8769972144269893
- `b4041` plsB growth=0.876997214426881
- `b2533` suhB growth=0.876997214426972
- `b0048` folA growth=0.8769972144269593
- `b1779` gapA growth=0.7594428152438916
- `b4161` rsgA growth=0.8769972144269783
- `b0657` lnt growth=0.8769972144269754
- `b2235` nrdB growth=0.8769972144270192
- `b2411` ligA growth=0.8769972144270192
- `b0126` can growth=0.8769972144270192
- `b3650` spoT growth=0.8769972144269739
- `b2563` acpS growth=0.8769972144269785
