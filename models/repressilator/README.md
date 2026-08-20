# Elowitz2000 — Repressilator

Cradle's first fully curated model (Phase 4). A synthetic 3-gene repressor
ring (LacI ⊣ TetR ⊣ cI ⊣ LacI) that produces sustained oscillations —
Elowitz & Leibler (2000), *Nature* 403:335-338 (PMID 10659856), curated in
BioModels as [`BIOMD0000000012`](https://www.ebi.ac.uk/biomodels/BIOMD0000000012).

Ingested from the real, live BioModels record (not hand-authored, unlike
Phase 1's toggle switch) via `cradle.knowledge.http` and
`cradle.substrate.examples.repressilator`. BioModels had already
MIRIAM-annotated every species and reaction but left all 16 kinetic
parameters unannotated — a real gap by Cradle's stricter Layer 8 rule,
closed here by tracing each parameter back to the same curated record
(`biomodels.db:BIOMD0000000012`) before promotion.

## Files

- `repressilator.xml` — the SBML model, fully MIRIAM/CURIE-annotated.
- `experiment.xml` — the SED-ML uniform time-course description
  (t = 0–1000, 500 steps, KiSAO:0000019 / CVODE).
- `repressilator.omex` — the COMBINE archive bundling both; this is the
  artifact anyone should actually load and run.
- `curation.json` — Cradle's own curation record: which evidence checks
  passed, which adapters independently reproduced the result, and when.

## Reproducing it

```python
from cradle.registry import discover

for plugin in discover("simulation_adapter"):
    if plugin.entry_point_name in ("tellurium", "copasi"):
        result = plugin.instance.run({"combine_archive": "repressilator.omex"}, {})
        print(plugin.entry_point_name, "PX range:", min(result["trajectories"]["PX"]), max(result["trajectories"]["PX"]))
```

Both registered ODE adapters reproduce ~9 oscillation peaks and a peak
amplitude of ~2368 (arbitrary model units) from this archive alone — see
`tests/test_repressilator_curation.py`, which does exactly this against
the files in this directory, not a freshly rebuilt copy.
