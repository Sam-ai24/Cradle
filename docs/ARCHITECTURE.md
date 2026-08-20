# Cradle Architecture

Design principle: **standards define the swap boundaries, not Cradle's own code.**
Computational systems biology already has ~20 years of open standards for decoupling
"what a model means" from "what experiment to run" from "which engine executes it."
Cradle adopts that stack instead of inventing a parallel one, and reserves custom
engineering for the layers those standards don't reach (spatial/agent-based simulation,
molecular dynamics, AI models, data-source licensing gates, orchestration, and — the
biggest genuinely-unsolved gap found so far — interactive visualization).

## Layer 1 — Model definition: SBML (+ Antimony)

Models are authored in **Antimony** (human-readable DSL, BSD-3) and compiled to **SBML**.
SBML's `comp` package supports hierarchical composition/flattening, so "replace this
submodel with a better one" is a matter of swapping an SBML fragment, not rewriting code.
`fbc` standardizes constraint-based/genome-scale objects; `multi` and `spatial` extend to
rule-based and geometric models when needed.

**Gene regulation extension — SBML `qual`.** Boolean/qualitative gene-regulatory-network
models get their own official SBML Level 3 package, `qual`, so they slot in beside `comp`/
`fbc`/`multi`/`spatial` at this same layer rather than needing a separate format. Author
with **GINsim** or **BoolNet** (R, GPL — isolate). Unlike the continuous-kinetics side,
there is **no mature BioSimulators-registered engine that executes `qual` models** the way
COPASI/Tellurium execute ODEs — Layer 4 needs a custom adapter here, mirroring the
PhysiCell/CompuCell3D precedent (standard format, no ready-made engine registry).

**Molecular-interaction and complex-structure extension.** Multi-entity structure problems
(protein-protein, protein-ligand, protein-nucleic-acid complexes) are handled by a new AI
contract at Layer 5, not a new Layer 1 format — see below.

## Layer 2 — Experiment description: SED-ML

**SED-ML** describes *what to simulate and what to output* — algorithm choice is named via
the **KiSAO** ontology, not any engine's native API. This is the actual point where a
solver engine becomes swappable: the same SED-ML document should run unmodified on any
KiSAO-aware engine.

## Layer 3 — Packaging/provenance: COMBINE archive (OMEX)

Bundles model + SED-ML + metadata into one portable, reproducible zip. This is Cradle's
internal exchange and archival format — every run is a self-contained, re-runnable unit.

## Layer 4 — Execution/adapter: a BioSimulators-style contract

This is the highest-leverage decision in the whole architecture. **BioSimulators**
(biosimulators.org) already proved that a thin, reusable contract — one CLI shape
(`-i archive -o outdir`), one Python API (`exec_sed_task()`), one Docker image per engine,
algorithm identity via KiSAO, and an explicit `ALGORITHM_SUBSTITUTION_POLICY` for
"close enough" substitutions — lets a single SED-ML/COMBINE archive run unmodified across
a dozen-plus independent engines. Confirmed live today: COPASI, VCell, Tellurium, COBRApy,
BioNetGen, PySB, MCell, Smoldyn, E-Cell4. Cradle's core **never calls a solver directly**,
only this adapter contract.

Important boundary: this contract stops at the well-mixed/kinetic level. Spatial and
agent-based engines (PhysiCell, CompuCell3D) aren't expressible in plain SBML/SED-ML, so
Cradle defines its **own** lightweight "spatial experiment" archive for that tier, reusing
COMBINE's zip+manifest pattern but with tool-specific payloads.

**Default engines to embed first** (chosen for license + embeddability, see RESOURCES.md
for the full comparison):
- **Tellurium / libRoadRunner** (Apache-2.0, Python-native) — default ODE/SSA engine, no
  container overhead for the common case.
- **COBRApy** (GPL/LGPL) — flux-balance/genome-scale metabolism. Because of its license,
  run it as an isolated subprocess/service behind the adapter contract, never statically
  linked into an Apache-licensed core.
- **basico/COPASI** (Artistic-2.0) — parameter estimation, hybrid simulation, profile
  likelihood (see Layer 8).
- **CompuCell3D** (MIT) — first spatial engine; genuine headless Python API.
- Later: **PhysiCell** (BSD-3, higher-fidelity agent-based tissue), **Smoldyn** (best
  maintained particle-based spatial-stochastic engine) or **E-Cell4** (spans ODE→SSA→
  particle-based in one API, but GPL-3.0 — isolate as a container).

**A third execution tier — molecular dynamics / coarse-grained.** Below well-mixed kinetics
and above/beside spatial agent-based simulation sits atomistic and coarse-grained physics
(membrane behavior, conformational dynamics, ligand binding at the physics level — this is
what "molecular interactions" means mechanistically, distinct from the AI-predicted
structures/complexes in Layer 5). As with the spatial tier, **no BioSimulators-equivalent
registry exists for MD** — MDTraj/MDAnalysis are engine-agnostic *analysis*-side trajectory
readers, not a simulation-*definition* contract the way SED-ML is. Cradle defines its own
minimal MD-tier contract: a structured manifest (topology + force-field parameters +
integrator settings) as input, **H5MD** (HDF5-based, open spec) as the standardized
trajectory output.

- **OpenMM** (MIT/LGPL) — default embeddable adapter. The only engine here that is
  simultaneously permissively licensed, a native in-process Python API (not a CLI/
  subprocess wrapper), GPU-accelerated, and supports MARTINI-style coarse-grained force
  fields.
- **GROMACS via gmxapi** (LGPLv2.1+) — second adapter for users needing its specific
  performance/ecosystem; gmxapi orchestrates GROMACS processes rather than embedding
  in-process, so treat it as a process-isolated adapter.
- **LAMMPS** (GPLv2) — optional third adapter, isolate like COBRApy/Smoldyn/E-Cell4; useful
  for coarse-grained/mesoscale work specifically.
- **NAMD is explicitly excluded as a default.** Its license is non-commercial-use-only
  (University of Illinois), the same restriction pattern as AlphaFold3 — not compatible
  with an openly redistributable platform. Leave it as an optional bring-your-own-license
  bridge for academic-only deployments, never bundled.
- **Prioritize coarse-grained (MARTINI-class) capability over raw atomistic MD.** Full-atom
  MD of an entire cell is intractable at meaningful timescales even in landmark efforts
  (e.g. the JCVI-syn3A minimal-cell MD work); MARTINI-style coarse-graining buys 2-3 orders
  of magnitude in reachable length/timescale and is the version of this tier that's
  actually useful at cell scale in the near term.

## Layer 5 — AI/foundation-model layer: typed contracts, not one generic interface

A single "call any model" interface fails the moment perturbation predictors, structure
predictors, and embedding models have genuinely different I/O shapes. Instead, Cradle
defines a small set of **typed contracts**, versioned and containerized like the
simulation adapters, with a conformance test gating registration (mirroring
`Biosimulators_test_suite`):

| Contract | I/O shape | First implementation |
|---|---|---|
| Embedding/representation | AnnData/h5ad in → embedding matrix + provenance out | Geneformer (Apache-2.0) |
| Perturbation predictor | baseline state + perturbation spec → predicted delta + uncertainty (see extension below) | TranscriptFormer (MIT) first; CellOracle (gated, mechanistic) and Arc State (gated) later |
| Sequence/genome model | sequence + task → score/generation/variant-effect | Evo2 (Apache-2.0) |
| Structure predictor | sequence(+MSA) → 3D coords + per-residue confidence | **OpenFold** (Apache-2.0 code, CC BY 4.0 AF2 weights) — **not** AlphaFold3 |
| Network inference | expression (+ optional accessibility/motif priors) → weighted TF→target graph + provenance | pySCENIC + GRNBoost2 (GPL-3.0 — isolate) |
| Molecular interaction predictor | 2+ entities (sequence and/or structure, each with a role) + optional binding-site constraints → ranked complex poses + interface confidence + binding affinity + affinity confidence | **OpenFold3** (Apache-2.0 co-folding) + **Boltz-2** (MIT, structure+affinity) + **AutoDock Vina** (Apache-2.0, classical/fast) |
| Reasoning/orchestration agent | NL task + tool manifest → plan + structured tool calls into the above | Claude via MCP tool-calling |

The orchestration agent never touches raw tensors — it calls the other contracts as tools,
following Anthropic's own MCP-connector pattern for life-sciences tool use rather than
doing biology math itself. For the orchestration layer's own model calls (routing between
LLM providers), adopt **LiteLLM** (MIT) directly rather than building a router — it already
normalizes 100+ providers behind one schema with fallback/load-balancing.

**Why network inference and molecular interaction are separate contracts, not variants of
existing ones.** Attention/embedding probes from Geneformer/scGPT capture co-expression,
not validated causal regulation — unreliable as a GRN source, so gene regulation needs its
own mechanistic-or-inferred contract the same way metabolism has both COBRApy (mechanistic)
*and* AI embeddings side by side. Molecular interaction has a genuinely different I/O shape
than single-sequence structure prediction (multiple entities, a pose ranking, an affinity
score) — collapsing it into the structure-predictor contract would hide that difference
rather than surface it.

**The perturbation-predictor contract needs a real extension, discovered by validating
against actual intervention data.** The original single-shape "baseline + spec → delta +
uncertainty" design only cleanly fits CRISPR/Perturb-seq-style perturbations. Validating
against the other three named intervention types in the mission (drugs, environmental
stress, aging) surfaced that the contract must support multiple output shapes selected by
the perturbation spec's `kind` field:

| Intervention type | Needed extension | Reference data |
|---|---|---|
| Gene edit (KO/KD) | fits as-is (baseline + spec → delta) | scPerturb, CRISPRbrain |
| Gene-fitness screen | needs a **scalar-phenotype** output mode, not a vector delta | DepMap Achilles (⚠ license forbids AI-training use, see NOTICE.md) |
| Drug | needs a **dose/time axis** in the spec and a **curve-shaped** output option (dose-response), not a single point | LINCS L1000/CMap, ChEMBL |
| Environmental stress | needs an **intensity axis** + a **pathway-summary** output option (data here is bulk/pathway-level, not single-cell) | ASTRA (⚠ CC BY-NC 4.0, non-commercial only) |
| Aging | needs a **longitudinal/trajectory** output mode (age-indexed sequence of deltas, not one snapshot) | Tabula Muris Senis (already in CZ CELLxGENE Census) |

This is exactly the kind of correction the "replace components as better science appears"
principle is meant to absorb — the contract gets versioned and extended, existing
implementations that only support the basic shape keep working, and new ones opt into the
richer output modes.

**Licensing red flag — do not build a default path through AlphaFold3.** Its weights carry
a separate non-commercial-only license that also forbids training competing models on its
outputs. OpenFold (Apache-2.0 code, CC BY 4.0 AF2 weights) is the safe, redistributable
default; AF3 can exist as an optional, explicitly license-gated adapter for non-commercial
users only. Same pattern for ESM3/ESM C (Cambrian non-commercial license) and Arc State
(CC BY-NC-SA + non-commercial weights), and now also **AlphaFold-Multimer** (CC BY-NC 4.0
weights), **SCENIC+** and **CellOracle** (both custom non-commercial academic licenses),
and **HADDOCK** (free for non-profit only, paid Accelrys license for commercial) — all
second-wave, license-gated, never the default.

## Layer 6 — Data/knowledge layer: CURIE-addressed, license-gated connectors

Every entity Cradle touches (species, reaction, protein, cell type) is addressed by a
**CURIE** (`namespace:localID`) resolved through **identifiers.org / MIRIAM** — this is
what lets a backing database be swapped or deprecated without touching the data model,
and what makes every claim in a model traceable to a primary source (MIRIAM annotation
requirement, see Layer 8).

MVP knowledge layer (chosen for genuinely open licenses — CC0/CC-BY/MIT, safe to cache and
redistribute): **UniProt, RCSB PDB, AlphaFold DB** (structure predictions, not the
generation model — this is CC-BY-4.0 and fine), **Reactome, BioModels, BioGRID, STRING,
CZ CELLxGENE Census**, plus the **identifiers.org** resolver itself.

**License traps to gate, never bake in:** KEGG (redistribution/non-academic use requires a
paid license), BioCyc/BiGG (tiered, mostly paid beyond EcoCyc), BioNumbers (CC BY-NC —
noncommercial only), SABIO-RK (commercial terms unclear, verify per use). These become
optional adapters behind the same connector interface, toggled per-deployment based on the
user's license status — never a hard dependency of core functionality.

**Gene-regulation connectors** (no new contract needed — these are ordinary Layer 6 data
connectors): **RegulonDB** (Apache-2.0, *E. coli* gold standard), **CollecTRI** via
`decoupleR`/OmniPath (the recommended 2023+ successor to the now-stale DoRothEA/TRRUST),
**JASPAR** (open PFM data, GPL-3.0 code) for TF motif priors.

**Intervention-validation connectors**, one per named intervention type — several carry
real license constraints that must be gated, not assumed away:
- **Drugs**: LINCS L1000/CMap (free academic use via GEO/CLUE API, commercial requires
  contacting the Broad) and **ChEMBL** (CC BY-SA 3.0, fully open, dose-response data).
- **Gene edits**: **scPerturb** (harmonized open Perturb-seq, the best-fitting category)
  and **CRISPRbrain** (CC BY 4.0); **DepMap Achilles** for fitness screens — ⚠ its CC BY
  4.0 license carries an explicit carve-out **prohibiting use to train/develop/enhance ML
  or AI models** beyond internal research use. Treat DepMap as eval/benchmark data only,
  never training data, and enforce this at the connector level, not by convention.
- **Environmental stress**: **ASTRA** (Atlas of Stress Response Activity, 2025/2026) is
  the only current dedicated resource — ⚠ CC BY-NC 4.0, non-commercial only, and bulk/
  pathway-level rather than single-cell. This category will stay the thinnest-covered of
  the four; the connector should say so rather than imply parity with the others.
- **Aging**: **Tabula Muris Senis** is already ingested into CZ CELLxGENE Census — zero
  new connector work. **GenAge** (HAGR) is a curated reference-gene list, useful for
  scoring/annotation, not delta-training data.

## Layer 7 — Plugin/composition mechanism

Data connectors, non-SBML-expressible submodels, and AI-contract implementations register
via Python **entry_points** (`importlib.metadata`, stdlib — the same mechanism pytest uses
for its own plugins) and bind to `Protocol`/ABC interfaces through a dependency-injection
container. Every plugin package is semver'd; a **contract test suite** (Pact-style,
run in CI) verifies any newly registered adapter against its interface before it's usable
— a swap is machine-verified, not just hoped to work.

## Layer 8 — Scientific credibility (non-optional, not a later add-on)

- **FAIR4RS** compliance for the software itself: persistent DOI (Zenodo/Software
  Heritage), `codemeta.json`/`CITATION.cff`, explicit OSI license, versioned releases.
- **MIRIAM annotation** on every model entity — controlled-vocabulary CURIE + source
  publication. No unsourced numbers.
- **MIASE-compliant provenance** on every simulation run, serialized as SED-ML so a run is
  machine-reproducible, not just described in a paper's methods section.
- **Curated vs. non-curated tiering**, mirroring BioModels: a model is only "curated" once
  independently reproduced against its source publication and MIRIAM-annotated. Label
  every model/result with its tier, visibly, in every UI and export.
- **STRENDA-compliant provenance** for kinetic parameters (Km, kcat) — assay conditions
  traceable, not a bare number copied from a table.
- **Uncertainty as a first-class output**: profile-likelihood identifiability (COPASI/
  PyCoTools) or simulation-based inference/ABC posteriors wherever parameters are fit —
  never a point estimate presented without a confidence/identifiability diagnostic.
- **Benchmark publicly**: validate against the Arc Institute Virtual Cell Challenge and
  VCBench before claiming predictive power on anything AI-layer-derived.
- **Licensing of Cradle itself**: Apache-2.0 core (patent grant, safer for institutional/
  commercial contributors than MIT). Audit every wrapped dependency individually — GPL
  dependencies (COBRApy, Smoldyn, E-Cell4) stay process/container-isolated, never
  statically linked into the Apache-licensed core.

## Layer 9 — Orchestration & reproducible execution

**CWL** (Apache-2.0, stable spec) describes pipelines independent of the engine that runs
them (cwltool/Toil/Cromwell) — the workflow-level analogue of SED-ML. **Nextflow**
(Apache-2.0) or **Snakemake** (MIT) execute the DAG; each step runs in a container
(**Apptainer** for HPC/cluster, Docker for cloud/dev) pinned to a specific engine/solver/
AI-model version. This is what makes "component X was upgraded from v1 to v2" a
config/container change with a full audit trail, not a code migration.

## Layer 10 — Visualization & interactive exploration

The mission's "explore the cell from whole-cell behavior down to organelles, pathways, and
molecular events, apply perturbations, compare alternative futures" describes a genuine
gap: **no existing open-source tool does "zoom from whole cell to molecule" for mechanistic
simulation output** — not CZI's Virtual Cells Platform, not COPASI/VCell (which have basic
plots but no scenario-diff UI), nothing found in a dedicated search. Cradle has to build
the compositing layer; it can still borrow the renderer components and the coordination
pattern.

**Renderers, registered as ordinary swappable plugins, one per scale band:**
- **Mol\*** (MIT, web-component, the PDBe/RCSB reference implementation) — molecular/
  structural scale. Not ChimeraX — non-commercial license, desktop-only, wrong shape for a
  web-embeddable plugin anyway.
- **Cytoscape.js** (MIT, general-purpose network rendering) for pathway/regulatory
  networks, with **Escher** (MIT, `opencobra/escher`) as an optional plugin specifically
  for metabolic flux maps.
- **Simularium** (Allen Institute, modified BSD, free non-commercial) for cellular/spatial
  agent-based output — already has published PhysiCell-to-Simularium converters, making it
  the natural renderer for Layer 4's spatial tier.
- **VTK.js** (BSD-3) for volumetric/organelle-geometry fields; **deck.gl** held in reserve
  for very large agent populations (100k+) where scene-graph renderers get heavy.

**The scale-router.** No off-the-shelf framework does the "zoom" compositing itself. The
closest architectural precedent is **Vitessce** (MIT) — built for multimodal single-cell/
spatial *omics*, not simulation, but its pattern is exactly right: linked views bound to a
shared state store, each renderer subscribing to the CURIE-addressed Layer 6 data and
activating at its own scale band as the camera crosses a zoom threshold. Cradle's
scale-router is modeled on this coordination pattern, built fresh rather than borrowed
wholesale.

**"Compare alternative futures."** No systems-biology tool has a first-class scenario-diff
UI (COPASI/VCell offer parameter scans, not run-vs-run comparison). Build this as
**small multiples**: N synchronized instances of whichever renderer is active, each bound
to a different run's CURIE-addressed output, sharing one camera/time-slider controller —
this pattern generalizes better for trajectory comparison than overlaying runs in one view.

## Interface

Ship a first-class **Jupyter**-native API (this is the actual medium of computational
biology, not a bespoke GUI) for programmatic/lab use, with outputs (files, provenance
metadata, COMBINE archives) structured to be ELN/LIMS-friendly for lab compliance
workflows. The Layer 10 visual explorer is the complementary, non-programmatic surface for
the same underlying data and runs — both read from the same CURIE-addressed layer, neither
is the "real" interface with the other as an afterthought.
