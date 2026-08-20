# NOTICE

Cradle is licensed under the Apache License, Version 2.0 (see `LICENSE`).

Copyright 2026 the Cradle project contributors.

## Third-party license isolation

Cradle's core is Apache-2.0. Some simulation-engine adapters wrap GPL/LGPL-licensed
tools. Per `docs/ARCHITECTURE.md` (Layer 8), these run **process- or container-isolated**
— invoked as a subprocess or Docker container, never statically linked into the core —
so their copyleft terms don't propagate to the rest of the codebase:

| Dependency | License | Isolation requirement |
|---|---|---|
| COBRApy | GPL / LGPL v2+ | Subprocess or container adapter only |
| Smoldyn | GPL-3.0 (source) / LGPL-3.0 (packaged) | Subprocess or container adapter only |
| E-Cell4 | GPL-3.0 | Subprocess or container adapter only |
| LAMMPS | GPLv2 | Subprocess or container adapter only |
| BoolNet (SBML-qual authoring) | GPL | Subprocess or container adapter only |
| pySCENIC / GRNBoost2 (network inference) | GPL-3.0+ | Subprocess or container adapter only |

GROMACS (LGPLv2.1+) and OpenMM (MIT/LGPL) both explicitly permit linking into proprietary/
commercial applications — no isolation requirement beyond normal LGPL dynamic-linking
hygiene.

## Restricted-data source gating

The following data sources have redistribution or commercial-use restrictions and must
stay behind an explicit, opt-in license gate (see `docs/RESOURCES.md`) — never a hard
default dependency:

- KEGG — commercial/redistribution use requires a paid license from Pathway Solutions
- BioCyc / BiGG (non-EcoCyc data) — tiered, mostly paid beyond academic EcoCyc use
- BioNumbers — CC BY-NC 2.0, non-commercial only
- SABIO-RK — terms unclear as of Aug 2026, verify before use
- ASTRA (stress-response atlas) — CC BY-NC 4.0, non-commercial only

**DepMap (Achilles CRISPR screens, PRISM drug-viability screens) needs a different kind of
gate**, not a commercial/non-commercial toggle: its CC BY 4.0 license carries an **explicit
carve-out prohibiting use to train, develop, or enhance ML/AI models** beyond internal
research use. This means DepMap data may be used for *evaluation/benchmarking* of Cradle's
perturbation-predictor contract but must never enter a training pipeline. Enforce this
distinction at the connector level (a `training_eligible: false` flag on the record, not
just a comment), since it's easy to violate by accident once the data is cached alongside
training-eligible sources like scPerturb.

## AI model weight licensing

- **AlphaFold3** weights are non-commercial-only and forbid training competing models on
  their output. Not used as a default; available only as an explicitly gated,
  non-commercial adapter. **AlphaFold-Multimer** weights carry the same CC BY-NC 4.0
  restriction — same gate, use **OpenFold3** instead (Apache-2.0, matches AF3 accuracy).
- **ESM3 / ESM C** weights ship under the Cambrian Non-Commercial License — gated,
  requires a separate commercial license from EvolutionaryScale before commercial use.
- **Arc State** code is CC BY-NC-SA 4.0 and weights are under Arc's non-commercial
  research license — gated, second-wave adapter only.
- **SCENIC+** and **CellOracle** (gene-regulatory-network tools) both carry custom
  non-commercial academic-use licenses — gated. Use **pySCENIC + GRNBoost2** (GPL-3.0,
  isolate per the table above) as the default, license-clean network-inference path.
- **HADDOCK** (protein-protein docking) is free for non-profit use only; commercial use
  requires a paid Accelrys license — gated. Use **OpenFold3**, **Boltz-2** (MIT), or
  **AutoDock Vina** (Apache-2.0) instead.
- **NAMD** is non-commercial-use-only (University of Illinois license) — excluded as a
  default MD engine; **OpenMM** is the safe default.
- **UCSF ChimeraX** is source-available but non-commercial — not bundled; at most an
  optional external-tool bridge for users with their own license, never a default
  visualization renderer (use Mol* instead).

Re-verify every license in this file before any commercial deployment decision — these
terms can change.
