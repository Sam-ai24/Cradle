# Cradle Resources

Reference tables from deep research conducted August 2026. Re-verify licensing terms
before any commercial deployment decision — these pages change.

## Standards (the swap boundaries)

| Standard | Purpose | Link |
|---|---|---|
| SBML (+ comp, fbc, multi, spatial) | Model definition, composition | sbml.org |
| Antimony | Human-readable authoring DSL → SBML | sys-bio/antimony (BSD-3) |
| SED-ML + KiSAO | Experiment description, algorithm identity | sed-ml.org |
| COMBINE archive (OMEX) | Model+experiment+metadata packaging | combine-org/combine-specifications |
| BioSimulators | Engine-agnostic execution contract + registry | biosimulators.org, docs.biosimulations.org |
| CWL | Pipeline description independent of runner | commonwl.org |
| identifiers.org / MIRIAM | CURIE resolution for cross-database entity IDs | identifiers.org |
| MIASE | Minimum info for a reproducible simulation experiment | PLOS Comp Bio 10.1371/journal.pcbi.1001122 |
| STRENDA | Kinetic-data reporting standard | beilstein-institut.de/en/projects/strenda |
| FAIR4RS | FAIR principles for research software | ardc.edu.au/resource/fair-principles-for-research-software-fair4rs |

## Simulation engines

### Small-network kinetics / signaling / metabolism

| Tool | Embeddable | Model class | License | Maintenance (Aug 2026) | Link |
|---|---|---|---|---|---|
| COPASI (basico) | Yes, Python bindings | ODE, Gillespie SSA, hybrid, steady-state/MCA | Artistic-2.0 | Active, v4.47 | github.com/copasi/COPASI |
| VCell (pyvcell) | Yes, REST + local solvers | ODE, spatial PDE, particle spatial-stochastic | MIT | Active | github.com/virtualcell/vcell |
| Tellurium / libRoadRunner / Antimony | Yes, Python-native | ODE (CVODE) + Gillespie SSA | Apache-2.0 | Active, roadrunner v2.10.0 | github.com/sys-bio/roadrunner |
| COBRApy | Yes, pure Python | Constraint-based FBA, genome-scale | GPL/LGPL v2+ | Active | github.com/opencobra/cobrapy |
| BioNetGen (PyBioNetGen) | Yes, CLI wrapper | Rule-based → ODE/SSA | MIT | Active | github.com/RuleWorld/bionetgen |
| PySB | Yes, native Python | Rule-based (via BioNetGen/Kappa backend) | BSD-2 | Active, v1.17.0 | github.com/pysb/pysb |
| Julia SciML (DifferentialEquations.jl, Catalyst.jl) | Via juliacall/PythonCall | ODE/SDE/DDE/DAE + jump/SSA | MIT | Very active | github.com/SciML |

### Spatial / multicellular / particle-based

| Tool | Embeddable | Model class | License | Maintenance (Aug 2026) | Link |
|---|---|---|---|---|---|
| CompuCell3D | **No PyPI/pip package at all (confirmed Aug 2026) — conda-only, blocked here** | Cellular Potts + PDE fields | MIT | Active, v4.9.0 | github.com/CompuCell3D/CompuCell3D |
| PhysiCell | **No PyPI/pip package at all (confirmed) — C++/Makefile only, blocked here** | Agent-based 3D multicellular | BSD-3 | Active (dev branch) | github.com/MathCancer/PhysiCell |
| Smoldyn | Installs cleanly; basic API works, but **retrieving positions via `listmols`/output-table segfaults, reproducibly, confirmed at minimal scale — blocked here** | Particle-based spatial stochastic | GPL-3.0 / LGPL-3.0 | Active | github.com/ssandrews/Smoldyn |
| E-Cell4 | **Implemented** (`plugins/ecell4_spatial/`) — `spatiocyte` module's object-level API (`list_particles_exact`) is clean and stable; one placement-performance gotcha found and worked around (rejection-sampling `Sphere` radius must be sized well above the target molecule count, or placement is pathologically slow) | ODE→SSA→particle (Spatiocyte/EGFRD), one API | GPL-3.0 — isolated as a subprocess (`ecell4_spatial.worker`), per NOTICE.md | Active | github.com/ecell/ecell4 |
| MCell | Not attempted — E-Cell4 already satisfied the exit criterion | Particle-based spatial stochastic + BNGL | MIT | Slowing (last commit ~May 2025) | github.com/mcellteam/mcell |

**BioSimulators registry coverage:** COPASI, VCell, Tellurium, COBRApy, BioNetGen, PySB,
MCell, Smoldyn, E-Cell4 are all live adapters today — swap between them by pointing the
same COMBINE archive at a different Docker image. **Not covered:** PhysiCell,
CompuCell3D — spatial geometry/agent rules aren't expressible in SBML/SED-ML, hence
Cradle's own spatial-archive format.

### Molecular dynamics / coarse-grained

| Tool | Embeddable | Model class | License | Maintenance (Aug 2026) | Link |
|---|---|---|---|---|---|
| OpenMM | Yes, native Python API (System/Integrator/Context objects) | Atomistic + coarse-grained (MARTINI-compatible) MD, GPU-accelerated | MIT/LGPL | **Implemented** (`plugins/openmm_md/`) — Green, installs cleanly on Windows, no build toolchain needed | github.com/openmm |
| GROMACS (gmxapi) | Python API orchestrates GROMACS processes, not in-process | Atomistic + coarse-grained MD | LGPLv2.1+ | Very active | gromacs.org |
| LAMMPS | Yes, Python wrapper | Atomistic + coarse-grained/mesoscale, mainly materials-science-rooted | GPLv2 | Active | lammps.org |
| NAMD | Yes (scriptable), but license-restricted | Atomistic MD | **Non-commercial-use-only (UIUC)** | Active | ks.uiuc.edu/Research/namd |
| MDTraj / MDAnalysis | Yes, Python | Engine-agnostic trajectory *analysis* (not a simulation-definition contract) | LGPLv2.1+ | Active | github.com/mdtraj/mdtraj |
| H5MD | — (file format, not a tool) | Standardized MD trajectory output format | GPLv3+ (open spec) | Active | h5md.nongnu.org |

No BioSimulators-equivalent registry exists for MD — Cradle defines its own minimal
contract (topology + force-field + integrator manifest in, H5MD trajectory out). Given
whole-cell-scale ambitions, coarse-grained (MARTINI-class) capability is the practical
near-term target; full atomistic MD of an entire cell is intractable at meaningful
timescales even in landmark efforts.

## Visualization / interactive exploration

| Tool | Scale | License | Embeddable | Maintenance (Aug 2026) | Link |
|---|---|---|---|---|---|
| Mol\* (Molstar) | Molecular/structural | MIT | Yes, web component | Active | github.com/molstar/molstar |
| NGL Viewer | Molecular/structural (lighter-weight fallback) | MIT | Yes, WebGL | Slower cadence | github.com/nglviewer/ngl |
| UCSF ChimeraX | Molecular/structural, desktop | **Non-commercial license** | No (desktop app) | Active | rbvi.ucsf.edu/chimerax — **do not bundle** |
| Cytoscape.js | Pathway/regulatory network, general | MIT | Yes, JS library | Active | js.cytoscape.org |
| Escher | Metabolic flux maps specifically | MIT | Yes, D3/JS | Active | github.com/opencobra/escher |
| Simularium | Cellular/spatial agent-based | Modified BSD, free non-commercial | Yes, web-based 3D viewer | Active | simularium.allencell.org |
| VTK.js | Volumetric/organelle geometry fields | BSD-3 | Yes | Active (v30) | github.com/Kitware/vtk-js |
| deck.gl | Very large agent populations (100k+) | MIT | Yes | Active | deck.gl |
| Vitessce (coordination pattern) | N/A — linked-view/shared-state architecture reference, not a renderer itself | MIT | Yes | Active | github.com/vitessce/vitessce |

No existing tool does "zoom from whole cell to molecule" for simulation output — confirmed
by direct search, including checking whether CZI's Virtual Cells Platform has one (it
doesn't). Cradle's scale-router is custom, modeled on Vitessce's linked-view pattern.

## Data / knowledge sources

| Source | Access | License (data) | Redistribution-safe? | Link |
|---|---|---|---|---|
| UniProt | REST + bulk | CC BY 4.0 | Yes | uniprot.org |
| RCSB PDB | REST + GraphQL | CC0 | Yes | rcsb.org |
| AlphaFold DB (structures) | REST + bulk | CC BY 4.0 | Yes | alphafold.ebi.ac.uk |
| Reactome | REST + bulk | CC0 | Yes | reactome.org |
| BioModels | REST + FTP | CC0 | Yes | ebi.ac.uk/biomodels |
| BioGRID | REST + bulk (free key) | MIT | Yes | thebiogrid.org |
| STRING | REST + bulk | CC BY 4.0 (some datasets need signed license) | Mostly | string-db.org |
| IntAct | PSICQUIC + bulk | CC BY 4.0 (trending CC0) | Yes | ebi.ac.uk/intact |
| CZ CELLxGENE Census | Python/R API (TileDB-SOMA) | Code MIT, data CC-BY | Yes, with attribution | cellxgene.cziscience.com |
| Human Cell Atlas | DCP APIs + bulk | CC BY 4.0 | Mostly (raw data has per-project caveats) | humancellatlas.org |
| Tabula Sapiens | CELLxGENE/Figshare/S3 | CC BY 4.0 processed; raw FASTQ under DUA | Processed only | tabula-sapiens.sf.czbiohub.org |
| identifiers.org / MIRIAM | REST resolver | Open registry | — (glue layer, not a data source) | identifiers.org |
| **KEGG** | REST (rate-limited) / paid bulk | **Commercial/redistribution needs paid license** | **No — gate it** | kegg.jp/kegg/legal.html |
| **BioCyc / EcoCyc** | Pathway Tools / bulk | **Tiered — EcoCyc free academic, rest paid** | **No — gate it** | biocyc.org |
| **BiGG Models** | REST + bulk | **Data restricted to academic/non-profit** | **No — gate it** | bigg.ucsd.edu |
| **BioNumbers** | Web/bulk only | **CC BY-NC 2.0, noncommercial only; also stale (~2010)** | **No — gate it, and treat as historical reference only** | bionumbers.hms.harvard.edu |
| **SABIO-RK** | REST | Terms unclear/JS-rendered, commercial unclear | **Verify per use — gate it** | sabiork.h-its.org |
| BRENDA | SOAP + bulk (free registration) | CC BY 4.0, possible Nagoya Protocol obligations | Mostly — check per commercial use case | brenda-enzymes.org |
| Human-GEM | GitHub (SBML/YAML/MAT) | CC-BY-4.0 | Yes | github.com/SysBioChalmers/Human-GEM |

## AI / foundation models

| Model | Contract type | Code license | Weights license | Status |
|---|---|---|---|---|
| Geneformer | Embedding | Apache-2.0 | Ungated, HF | **Green — default** |
| scGPT | Embedding/annotation | MIT | Open | Green |
| TranscriptFormer | Perturbation/cross-modal | MIT | Open | **Green — default**, strongest 2026 VCBench result |
| Evo2 | Sequence/genome | Apache-2.0 | Open, HF | **Green — default** |
| OpenFold | Structure | Apache-2.0 | AF2 weights CC BY 4.0 | **Green — default structure predictor** |
| AlphaFold3 | Structure | Apache-2.0 (code) | **Non-commercial only; forbids training competing models on outputs** | **Red flag — gate, non-commercial deployments only** |
| ESM3 / ESM C | Structure/sequence | — | Cambrian Non-Commercial License | **Yellow/red — needs separate commercial license from EvolutionaryScale** |
| Arc State | Perturbation | CC BY-NC-SA 4.0 | Non-commercial research license | **Yellow/red — gate, second wave** |
| scFoundation | Embedding | Apache-2.0 (code) | Custom "Model License" | Yellow — review before use |
| CodonFM (NVIDIA) | Sequence | Apache-2.0 (code) | NVIDIA Open Model License | Yellow — review before use |
| CZI rBio, GREmLN | Reasoning / GRN | Via CZI Virtual Cells Platform | Check per-model | Review before use — VCP is a curated hub, not an enforced API |
| Claude (via MCP) | Reasoning/orchestration | — | Anthropic API terms | Used as orchestrator, not a biology-math engine |
| LiteLLM | Provider gateway for the orchestration layer | MIT | — | **Green — adopt directly** |
| pySCENIC + GRNBoost2 (`arboreto`) | Network inference | GPL-3.0+ / BSD-3 | Open | **Red flag (Aug 2026) — confirmed broken against current `dask`/`distributed` by direct install+run: `TypeError: Must supply at least one delayed object`. Not merely stale; do not build on it without pinning a compatible dask stack.** |
| GRNBoost2 algorithm, reimplemented directly (scikit-learn) | Network inference | BSD-3 (scikit-learn) | Open | **Green — Cradle's actual default** (`plugins/grn_inference/`), same algorithm without arboreto's broken orchestration layer |
| SCENIC+ | Network inference | Custom, non-commercial academic only | Gated | **Red flag — second wave** |
| CellOracle | Perturbation (mechanistic GRN-based) | Modified Apache-2.0, non-commercial academic only | Gated | **Red flag — second wave, contact Morris Lab for commercial** |
| OpenFold3 | Molecular interaction (co-folding: protein/nucleic-acid/ligand complexes) | Apache-2.0 | Open | Green — default candidate, not yet implemented (deferred, see docs/ROADMAP.md Phase 7) |
| Boltz-2 | Molecular interaction (structure + binding affinity, joint) | MIT | Open, commercial-cleared | Green — default candidate, not yet implemented |
| AutoDock Vina (Smina as fork option) | Molecular interaction (classical docking) | Apache-2.0 | Open | **Yellow (Aug 2026, Windows) — the `vina` PyPI package requires Boost and has no prebuilt Windows wheel, confirmed by direct install attempt (`ValueError: Boost library location was not found!`). License/algorithm are still fine; this is a platform-specific build gap, not a license or design problem.** |
| AlphaFold-Multimer | Molecular interaction (complex structure) | Apache-2.0 (code) | **CC BY-NC 4.0 — non-commercial only** | **Red flag — gate, use OpenFold3 instead** |
| HADDOCK | Molecular interaction (protein-protein docking) | Free non-profit only | **Paid Accelrys license for commercial** | **Red flag — gate** |
| DiffDock / DiffDock-PP | Molecular interaction (diffusion-based pose sampling) | MIT | Open | Green — optional secondary adapter |

## Gene regulation

| Resource | Type | Access | License | Status | Link |
|---|---|---|---|---|---|
| RegulonDB | Curated regulatory network (*E. coli*) | REST/bulk via `regutools` | Apache-2.0 | **Green — gold standard default** | regulondb.ccg.unam.mx |
| CollecTRI | Curated TF→target interactions | Via `decoupleR`/OmniPath | Open (license param governs included sources) | **Green — recommended 2023+ successor to DoRothEA** | github.com/saezlab/CollecTRI |
| DoRothEA | Curated TF→target interactions | Via `decoupleR` | Open | Superseded by CollecTRI — keep as fallback only | — |
| TRRUST | Curated TF→target interactions | Bulk | Open | **Stale since 2018 — historical reference only** | — |
| JASPAR | TF binding motifs (PFMs) | REST | Data open, code GPL-3.0 | **Green — needed for SCENIC-style motif priors** | jaspar.elixir.no |
| ENCODE cCREs | Candidate regulatory elements | Bulk BED via SCREEN/UCSC | Terms less standardized — verify before caching | Verify per use | — |
| SBML `qual` + GINsim / BoolNet | Boolean/qualitative GRN modeling standard + authoring tools | — | Spec open; BoolNet is GPL (isolate) | **Green (spec) / isolate (BoolNet)** — no mature registered execution engine yet | sbml.org/documents/specifications/level-3/version-1/qual |

## Intervention-validation datasets

| Category | Resource | Access | License | Contract-shape note |
|---|---|---|---|---|
| Drugs | ChEMBL | REST — **implemented** (`plugins/chembl_data/`) | CC BY-SA 3.0 | Real IC50 → Hill-equation `dose_curve`, live-verified |
| Drugs | LINCS L1000 / CMap | CLUE API returned empty without a registered key; GEO bulk not attempted | Free academic; commercial needs Broad contact | **Deferred, gated like BioGRID** — ChEMBL alone already satisfies the exit criterion for this category |
| Gene-fitness screens | DepMap Achilles | Bulk CSV (~98MB), direct Figshare URL — **implemented** (`plugins/depmap_data/`) | CC BY 4.0 **with explicit no-AI-training carve-out, enforced as a real `training_eligible: False` field, not just documented** | Real gene-effect scores → `scalar_phenotype`, live-verified |
| Gene edits | scPerturb | Zenodo REST API for metadata; **implemented for 2 of ~30 files** (`plugins/scperturb_data/`) — most files are 250MB-2.5GB, but the smallest (45-121MB) are genuinely tractable, confirmed by downloading them | CC BY 4.0 (verify per-study terms) | Real Perturb-seq (Dixit&Regev 2016 CRISPR + Aissa&Benevolenskaya 2021 drug) → `vector_delta`, live-verified, including the perturbed gene's own delta |
| Gene edits | CRISPRbrain | No discoverable REST API in a reasonable search | CC BY 4.0 | Deferred — scPerturb already covers this category |
| Environmental stress | ASTRA | **No discoverable REST API** — JS SPA shell only at every guessed path | CC BY-NC 4.0, non-commercial only | **Deferred — thinnest-covered category, as predicted when this phase was planned** |
| Aging | Tabula Muris Senis | Direct H5AD download via CZ CELLxGENE Discover (~69MB for one tissue) — **implemented** (`plugins/aging_expression_data/`) | CC BY 4.0 | Real per-age-group expression → `trajectory`, live-verified; the canonical senescence marker (Cdkn2a) does *not* show a clean monotonic increase in this specific tissue slice — reported honestly, not cherry-picked around |
| Aging | GenAge (HAGR) | Bulk | Open | Curated reference genes, scoring only — not delta-training data, not implemented |
| Aging | Digital Ageing Atlas | Bulk | CC BY 3.0 | **Stale since ~2015 — reference only** |

## Benchmarks to validate against

- **Arc Institute Virtual Cell Challenge** — cell.com/cell/fulltext/S0092-8674(25)00675-0
- **VCBench** (2026) — biorxiv.org/content/10.64898/2026.06.18.733146v1 — evaluates
  Geneformer, scGPT, UCE, TranscriptFormer, Arc State across perturbation prediction,
  cross-species generalization, GRN inference, temporal dynamics, multi-scale integration.

## Landmark prior art

- Karr/Covert whole-cell model of *M. genitalium* (2012, MIT license) —
  github.com/CovertLab/WholeCell — the reference architecture for "28 submodels, one
  organism," useful as a mechanistic-composition case study even though Cradle's own
  composition layer (SBML `comp`) is more general.
- CZI Virtual Cells Platform — chanzuckerberg.github.io/virtual-cells-platform — largest
  funded effort in this space; hosts rBio, TranscriptFormer, GREmLN, CodonFM; submission
  is currently manual curation (Airtable review), not an enforced API — a gap Cradle's
  BioSimulators-style contract is designed to avoid.
