# Cradle

Cradle is a cell simulation platform built to be scientifically credible (traceable to
real data, validated, uncertainty-aware) and permanently upgradeable — every data source,
simulation engine, submodel, and AI model is a swappable, versioned component, so the
system keeps absorbing better science and better models instead of being rewritten for them.

## Documents

- [`docs/HANDOFF.md`](docs/HANDOFF.md) — start here when picking this project back up:
  current phase-by-phase state, what's pending, and operational notes.
- [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) — how Cradle compares to the real competitive
  landscape (Karr/Covert whole-cell models, CZI's Virtual Cells Platform, Arc Institute's
  Virtual Cell Challenge, VCell/CompuCell3D/PhysiCell, single-cell foundation models), and
  what's actually required to reach "scientific grade."
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the layered design: what standard sits at
  each swap boundary, which open-source projects to build on vs. avoid reinventing, and why.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the phased, step-by-step build plan.
- [`docs/RESOURCES.md`](docs/RESOURCES.md) — reference tables: data sources, simulation
  engines, AI/foundation models, and scientific standards, each with license and maintenance
  status checked as of August 2026.

## Core design rule

No layer ever calls another engine/model/database directly. Every cross-layer call goes
through a standard, versioned contract (SBML/SED-ML/COMBINE for simulation, typed model
contracts for AI, CURIEs for data, entry_points for plugins). Swapping a component means
changing a config entry and passing a conformance test — never touching the code that
depends on it.

## Status

**Phase 0 (governance & scaffolding) — done.** The plugin/conformance mechanism is real
and proven: `src/cradle/contracts/` defines the three Protocol contracts, `src/cradle/registry.py`
discovers plugins via `entry_points`, and `src/cradle/conformance/` verifies any registered
plugin against its contract. Three reference plugins under `plugins/` (`hello_data`,
`hello_sim`, `hello_ai`) each register independently and pass conformance — proof that a
new plugin needs no change to Cradle's own code.

**Phase 1 (model & experiment substrate) — done.** `src/cradle/substrate/` compiles
Antimony to SBML, mechanically enforces a MIRIAM/CURIE annotation on every species,
parameter, and reaction, builds SED-ML experiments, packages COMBINE archives, and logs
MIASE-style run provenance. The proof case is real, not synthetic: the Gardner, Cantor &
Collins (2000) genetic toggle switch (BioModels BIOMD0000000507), fully sourced and
CURIE-annotated, round-trips end to end and reproduces its expected bistable behavior.

**Phase 2 (first simulation adapters) — done, validated at real scale 2026-08-21.** Three
registered `SimulationAdapter` plugins under `plugins/`: Tellurium/libRoadRunner and COPASI
(both run the Phase 1 toggle switch unmodified and agree numerically to within 0.1%) and
COBRApy for FBA (subprocess-isolated per its GPL/LGPL license). `cradle-conformance`
dispatches its check per adapter's declared `input_mode`, so real archive-based adapters get
checked against a real reference archive while the Phase 0 toy plugin keeps passing
unmodified. The COBRApy adapter was later run **unmodified** against a real genome-scale
model — **iML1515** (2,712 reactions, 1,516 genes, Monk et al. 2017) — predicting the
correct ~0.877/h glucose-minimal-media growth rate and correctly classifying real essential
(`murA`, `accA`) vs. non-essential (`lacZ`, `lacY`, `araA`) gene knockouts, the same
validation style Karr et al.'s 2012 whole-cell model used. See `docs/ROADMAP.md`'s Phase 2
addendum for a genuinely interesting nuance this surfaced (a `folA` knockout prediction
rescued by a real, independently documented redundant isozyme the model itself annotates).

**Phase 3 (knowledge/data layer) — done.** Seven `DataConnector` plugins hit real, live
APIs (UniProt, RCSB PDB, AlphaFold DB, Reactome, BioModels, STRING, CZ CELLxGENE Discover),
plus KEGG as the flagship license-gated example (off by default). BioGRID is implemented
but needs a registered API key to actually run — reported as a distinct "not configured"
skip, not a failure. `cradle.knowledge.router.resolve_all()` fans one query out across
every connector that accepts it; verified live against TP53 (`uniprot:P04637`), which
resolves across 5 real sources at once, each CURIE-linked and source-attributed.

**Phase 4 (first real validated model) — done.** Cradle's first curated model:
the Elowitz & Leibler (2000) Repressilator, ingested live from BioModels
(`BIOMD0000000012`) rather than hand-authored — and found a real gap by Cradle's own
stricter rule (16 unannotated parameters in an otherwise-curated source), closed before
promotion. `cradle.curation.promote_to_curated()` mechanically requires every evidence
check to pass and at least 2 independent adapters to agree; published to
`models/repressilator/` (SBML + SED-ML + COMBINE archive + curation record, real files in
the repo). Both registered adapters reproduce the sustained oscillation from that published
archive alone, loaded fresh from disk.

**Phase 5 (AI layer) — in progress.** The orchestration contract is done and real:
`claude` and `openrouter` adapters (`plugins/llm_orchestrator/`), both via LiteLLM, both
entirely optional. Neither requires a key to install or for the rest of Cradle to work —
without one, `cradle.ai.get_orchestrator()` and the conformance runner report a clear,
actionable "not configured" message (which env var, where to get a key) rather than a
failure or a silent no-op. Set `ANTHROPIC_API_KEY` and/or `OPENROUTER_API_KEY` (and
optionally `CRADLE_CLAUDE_MODEL` / `CRADLE_OPENROUTER_MODEL` to pick a specific model) to
turn either on. The embedding/sequence/structure/perturbation contracts (Geneformer, Evo2,
OpenFold, TranscriptFormer) are not yet built — see `docs/ROADMAP.md` for why that's a
separate, larger increment rather than a stub.

**Phase 6 (uncertainty & credibility hardening) — mostly done.** `cradle.estimation` +
`copasi_sim.estimation.estimate_parameters()` fit a parameter with COPASI and report a
real confidence interval, verified against a known ground truth (not just checked for
shape). The curation tier is now embedded *inside* the COMBINE archive itself, not only in
a sidecar file — a real libcombine bug surfaced and got fixed along the way (see
`docs/ROADMAP.md`). The knowledge layer now retries transient network failures with
backoff. FAIR4RS self-assessment is real (`docs/FAIR4RS_ASSESSMENT.md`) and found a
concrete open item: `CITATION.cff`/`codemeta.json` still need your real name — that, plus
an explicit decision on whether this repo goes public, is what's blocking an actual tagged
release. The VCBench benchmark bullet is explicitly deferred, not skipped: there's nothing
to benchmark until Phase 5's embedding/perturbation models exist.

**Phase 7 (molecular & regulatory tiers) — 3/4 done.** MD/coarse-grained (`plugins/openmm_md/`)
runs a real Langevin-thermostatted toy chain that equilibrates to its target temperature,
with full trajectories in a real H5MD file. Network inference (`plugins/grn_inference/`)
implements GRNBoost2's actual algorithm directly via scikit-learn after confirming
`arboreto`'s reference implementation is broken against current `dask` — validated against
synthetic ground truth (real driver, decoy, and noise genes, correctly ranked). SBML `qual`
Boolean-network execution (`plugins/boolean_qual_sim/`) needed no GINsim/BoolNet dependency
— two real bugs (an SBML attribute-ordering gotcha, a libsbml object-lifetime bug) got
caught and fixed along the way. Molecular interaction/docking is explicitly deferred:
AutoDock Vina needs Boost and has no Windows wheel, confirmed by a direct attempt, not
assumed — same footing as Phase 5's deferred heavy models.

**Phase 8 (intervention validation) — 3/4 done.** `cradle.perturbation` extends the
perturbation contract with a `kind` field (vector delta / scalar phenotype / dose curve /
trajectory), proven additive with a test that the original Phase 5 shape still validates
unchanged. `plugins/perturbation_baselines/` implements one honest **empirical baseline**
per kind — real ChEMBL IC50 data (drugs), real DepMap Achilles fitness scores (gene-fitness,
with a real `training_eligible: False` field enforced, not just documented), real scPerturb
Perturb-seq data (gene edits — the "too-big" files turned out to have small ones worth
actually checking), and real Tabula Muris Senis aging data (which honestly does *not* show
the textbook senescence-marker trend in this tissue slice — reported as found, not massaged).
Environmental stress (ASTRA) stays blocked: no discoverable REST API.

**Phase 9 (spatial/multicellular expansion) — done, with a different engine than planned.**
CompuCell3D (conda-only) and PhysiCell (C++-compile-only) both have no pip/PyPI path at
all; Smoldyn installs cleanly but has a confirmed, reproducible **segmentation fault**
retrieving molecule positions in this build — a real native crash, isolated down to the
smallest possible case before being ruled out. E-Cell4's `spatiocyte` module works cleanly
instead (`plugins/ecell4_spatial/`, subprocess-isolated like `cobrapy_fba` since it's
GPL-3.0) and is verified against the *exact* analytical solution of the diffusion equation
— particle-position spread growing as `sqrt(2·D·t)` from a point source, checked at 4
independent time points, not just a qualitative pattern.

**Phase 10 (visualization & interactive exploration) — core done.** `viz/` is a real,
browser-verified scale-router built on **Cytoscape.js** (pathway-scale network) and
**Mol\*** (molecular-scale structure): clicking a protein in the repression-ring network
loads its real AlphaFold structure, and a shared time-slider drives two synchronized SVG
charts comparing the Phase 2 Tellurium and COPASI adapters on the same published Phase 4
archive. `scripts/export_visualization_data.py` sources every node, edge, and CURIE from the
model's own real annotations rather than restating them, and found two genuine gaps along
the way: AlphaFold DB has no entry for one of the three proteins (a confirmed 404, not a
bug — the page says so honestly when that node is clicked), and AlphaFold's file server
sends no CORS header, so structures are downloaded once server-side rather than fetched live
by the browser. Escher/Simularium/VTK.js are not built — there's no volumetric or
spatial-simulation output yet to visualize with them.

**Phase 11 (lab-facing interface) — 3/4 done.** `cradle.lab` is a notebook-facing front door
onto Phases 1-9's existing capabilities — `notebooks/phase11_lab_workflow.ipynb` is a real,
executed notebook (outputs baked in, not hand-edited) that fits a parameter against synthetic
ground-truth data, applies the fit back into the model, simulates it on two independent
engines, confirms they agree, curates the result, and exports a lab-report Markdown file,
using only `cradle.lab` calls. The interactive ipywidgets explorer needs the new `lab` extra
and degrades gracefully without it, same shape as Phase 5's AI keys. `workflows/lab_pipeline.cwl`
is a real, valid CWL pipeline, but `cwltool` itself doesn't run natively on Windows (confirmed
via two concrete errors, not assumed) — `workflows/Snakefile` is the equivalent pipeline that
actually runs here, verified by a real subprocess-invoking test. `Dockerfile`/`Apptainer.def`
are written but unbuilt: no Docker or WSL2 is installed on this machine, a confirmed gap, not
a skipped step.

**Phase 12 (second-wave AI models & governance) — in progress.** `plugins/esmc_embedding/`
implements the embedding AI contract for real against ESM-C-300M, after directly checking
(not assuming) that this specific checkpoint is MIT-licensed and non-gated — correcting an
earlier assumption in `docs/ARCHITECTURE.md`/`NOTICE.md`. `plugins/geneformer_embedding/`
does the same for single-cell expression against **Geneformer** — the model Architecture
Layer 5 always named as the intended default, unbuilt since Phase 5 because a real install
was a genuinely multi-step problem (no PyPI package, a broken git clone, an unbuildable
native dependency deep in its own package init) rather than a license block; worked through
and disclosed rather than deferred, verified on real 10x Genomics PBMC cells. A real
benchmark check against the field's own simplest baseline (PCA on log-normalized
expression) found Geneformer's embedding substantially better at separating real,
published PBMC cell types — 88.0% vs. 23.6% 5-fold k-NN accuracy — using `sklearn` after
CZI's own `cz-benchmarks`/`scib-metrics` turned out blocked here too (`jaxlib` fails to
import under a Windows Application Control policy, a different, real blocker). See
`docs/ROADMAP.md`'s Phase 12 section and `docs/geneformer_benchmark.json` for the full
numbers. Four of the other five named
second-wave models (CellOracle, HADDOCK3, SCENIC+, AlphaFold3/-Multimer) are confirmed
blocked or deliberately deferred for real, disclosed reasons; Arc State installs cleanly but
needs multi-GB downloads and a training-run-directory input its more relevant model expects,
so it's deferred rather than rushed. `cradle.lab.bridges` gives NAMD/ChimeraX a real,
tested "is a user's own installation configured and runnable" check; translating Cradle's MD
manifest into NAMD's own config format is real work deliberately left unattempted untested.
`CONTRIBUTING.md` formalizes the plugin-contribution process, and the phase's own exit
criterion — an external contributor adding a working adapter with no core-team help — was
verified directly: a fresh agent given only the published docs built and shipped
`plugins/pubchem_data/`, a real PubChem connector that passes conformance, surfacing three
real documentation gaps now fixed. See `docs/ROADMAP.md` for the full account.

See `docs/ROADMAP.md` for what's next (finishing Phase 5's AI layer, Phase 7's docking
contract, Phase 8's environmental-stress category, Phase 10's remaining renderers, Phase
11's container build/test on a machine that actually has Docker or WSL2, or closing out
Phase 12's exit-criterion verification).

## Getting started (local dev)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat on cmd
pip install -e ".[dev,demo,lab,pipelines]" \
  -e plugins/hello_data -e plugins/hello_sim -e plugins/hello_ai \
  -e plugins/tellurium_sim -e plugins/copasi_sim -e plugins/cobrapy_fba \
  -e plugins/uniprot_data -e plugins/pdb_data -e plugins/alphafold_data \
  -e plugins/reactome_data -e plugins/biomodels_data -e plugins/string_data \
  -e plugins/biogrid_data -e plugins/cellxgene_data -e plugins/kegg_data \
  -e plugins/chembl_data -e plugins/depmap_data -e plugins/scperturb_data \
  -e plugins/aging_expression_data -e plugins/collectri_data -e plugins/pubchem_data \
  -e plugins/openmm_md -e plugins/grn_inference -e plugins/boolean_qual_sim \
  -e plugins/ecell4_spatial -e plugins/perturbation_baselines \
  -e plugins/llm_orchestrator -e plugins/esmc_embedding -e plugins/geneformer_embedding

cradle-conformance   # discovers + verifies every registered plugin (live network calls)
pytest -q            # same checks, plus the Phase 1-5 substrate + adapter + knowledge + AI tests
```

The `llm_orchestrator` plugin needs no key to install — without one, both adapters report
a clear "not configured" skip. To actually use AI orchestration, set `ANTHROPIC_API_KEY`
and/or `OPENROUTER_API_KEY` yourself (get one from Anthropic's console or openrouter.ai);
Cradle never ships or assumes a key of its own.

Optional, for full coverage: `CRADLE_BIOGRID_API_KEY=<your key>` (free registration at
webservice.thebiogrid.org) and `CRADLE_LICENSE_ACK_KEGG=1` (only after reading NOTICE.md's
KEGG terms — it's off by default for a reason).

To view the Phase 10 visualization, run the one-time export then serve the static folder:

```bash
python scripts/export_visualization_data.py   # writes viz/data/*.json + real structure PDBs
python -m http.server 8743 --directory viz    # then open http://localhost:8743
```

`viz/` loads Mol* and Cytoscape.js from a CDN (`jsdelivr`) — no npm/build step — and reads
only the local `viz/data/` files it just exported; nothing else is fetched live.

For the Phase 11 lab-facing tools, add the `lab` extra (`pip install -e ".[lab]"`) for the
notebook/widgets and `pipelines` (`pip install -e ".[pipelines]"`) for Snakemake:

```bash
pip install -e ".[lab,pipelines]"

# open notebooks/phase11_lab_workflow.ipynb in Jupyter, or rebuild+execute it fresh:
python scripts/lab_pipeline/build_notebook.py

# run the fit -> apply -> simulate -> benchmark pipeline (Snakemake; cwltool does not run
# natively on Windows, see docs/ROADMAP.md Phase 11):
python scripts/lab_pipeline/prepare_example_inputs.py
snakemake -s workflows/Snakefile --cores 1
```
