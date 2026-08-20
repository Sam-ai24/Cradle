# Cradle Roadmap

Each phase has an exit criterion. Don't start the next phase until the current one's
criterion is actually met — the whole point of this architecture is that later phases
plug into contracts, so the contracts have to be right before there's a lot built on them.

**Revised 2026-08-20** after checking the roadmap against the project's full mission
statement. Phases 7, 8, and 10 are new (molecular/regulatory tiers, intervention
validation, visualization); what were Phases 7-9 are renumbered to 9, 11, 12. This kind of
revision is expected to keep happening — the roadmap itself is a swappable component of
the project, not a fixed contract.

## Phase 0 — Governance & scaffolding — ✅ done (2026-08-20)

- Repo structure, Apache-2.0 LICENSE, per-dependency license audit spreadsheet (flag GPL:
  COBRApy, Smoldyn, E-Cell4 → must stay process/container-isolated).
- `CITATION.cff` + `codemeta.json` from day one (FAIR4RS).
- Define the plugin contract spec (entry_points groups, required Protocol interfaces) for
  three plugin kinds: data connector, simulation adapter, AI model adapter.
- CI skeleton: contract-conformance test runner (Pact-style) that runs whenever a plugin
  package is registered.

**Exit criterion:** a "hello world" plugin of each kind (data/simulation/AI) can register
and pass a trivial conformance test in CI.

**Met.** `src/cradle/` (contracts, registry, conformance runner) + three reference plugins
under `plugins/` (`hello_data`, `hello_sim`, `hello_ai`), each installed independently and
registering via `entry_points`. `cradle-conformance` and `pytest` both show 3/3 plugins
passing, with zero Cradle-core code referencing any specific plugin. No CI service is
wired up yet (local-only per current instructions) — the conformance runner itself is
CI-ready whenever a runner is connected.

## Phase 1 — Model & experiment substrate — ✅ done (2026-08-20)

- Antimony → SBML authoring pipeline; validate against `libsbml`.
- SED-ML generation for a basic time-course experiment; COMBINE archive packaging
  (`libcombine`).
- Entity model: every species/reaction/parameter carries a CURIE resolved via
  identifiers.org (MIRIAM). No entity without a source annotation.
- Run-provenance schema (MIASE fields) logged automatically for every simulation, stored
  alongside the archive.

**Exit criterion:** a hand-written toy model (e.g. a 3-reaction toggle switch) round-trips:
Antimony → SBML → SED-ML → COMBINE archive → run → provenance log, with every entity
CURIE-annotated.

**Met.** `src/cradle/substrate/` (`model.py`, `annotate.py`, `experiment.py`, `archive.py`,
`provenance.py`) plus a real, sourced example model in
`src/cradle/substrate/examples/toggle_switch.py`: the Gardner, Cantor & Collins (2000)
genetic toggle switch (Nature 403:339-342, doi:10.1038/35002131, curated in BioModels as
BIOMD0000000507), not an invented toy — its two species are annotated as the real proteins
(LacI, uniprot:P03023; bacteriophage lambda CI repressor, uniprot:P03034) and its four
parameters use the paper's actual fitted dimensionless values, each carrying a CURIE back
to the source. `require_entity_annotations()` mechanically rejects any species, parameter,
or reaction missing a CURIE — proven by a dedicated negative-path test, not just asserted.
The full round trip (Antimony → SBML → SED-ML → COMBINE archive → execute via
Tellurium/libRoadRunner → MIASE-style provenance JSON) passes in `tests/`, and the executed
model actually reproduces the expected bistable behavior (U and V resolve to opposite
stable states from initial conditions near the unstable midpoint). Tellurium/libRoadRunner
here is a demo-only execution path (`pip install -e .[demo]`) — Phase 2 formalizes it as a
registered `SimulationAdapter` plugin instead of a direct import.

## Phase 2 — First simulation adapters — ✅ done (2026-08-20)

- Wrap **Tellurium/libRoadRunner** as the default ODE/SSA adapter behind the BioSimulators-
  style contract (`exec_sed_task()` shape).
- Wrap **basico/COPASI** for parameter estimation + profile-likelihood identifiability.
- Wrap **COBRApy** for FBA, isolated as a subprocess (license isolation, see Phase 0).
- Contract-conformance tests for all three: same COMBINE archive, same KiSAO algorithm id,
  verify outputs agree within numerical tolerance across adapters where applicable.

**Exit criterion:** the same toy model from Phase 1 runs unmodified on two different
adapters (e.g. Tellurium and COPASI) and produces numerically consistent results — this is
the actual proof that the swap boundary works.

**Met.** Three registered `simulation_adapter` plugins: `cradle-plugin-tellurium-sim`,
`cradle-plugin-copasi-sim`, `cradle-plugin-cobrapy-fba` (`plugins/`). Tellurium and COPASI
both run the *same* Phase 1 toggle-switch COMBINE archive unmodified and agree numerically
to within 0.1% on both species' final values (`tests/test_simulation_adapters_agree.py`) —
proof the Layer 4 swap boundary actually works, not just that it's designed to. COPASI's
own native SED-ML importer proved unreliable in testing (it imported the model but silently
used default trajectory-task settings instead of the described duration/steps), so that
adapter parses the SED-ML itself via a new shared `cradle.substrate.experiment` reader and
drives `basico` directly — the same "parse the standard, drive the engine natively" pattern
a BioSimulators wrapper uses. COBRApy runs FBA on a synthetic toy network via a
subprocess-isolated worker (`cobrapy_fba.worker`, invoked as `python -m`, never imported
into cradle-core's process, per NOTICE.md's GPL isolation rule) and is verified against an
analytically obvious optimum, not just checked for output shape
(`tests/test_cobrapy_adapter.py`). The conformance mechanism itself grew a real capability
here: `check_simulation_adapter` now dispatches on each adapter's declared `input_mode`
(`toy_dict` / `combine_archive` / `fba_sbml`) so the Phase 0 `hello_sim` plugin keeps
passing unmodified while real adapters get checked against a real reference archive
(`cradle/conformance/fixtures.py`) — additive, not breaking.

## Phase 3 — Knowledge/data layer (MVP)

- Build connectors for the 8 open-license MVP sources: UniProt, RCSB PDB, AlphaFold DB,
  Reactome, BioModels, BioGRID, STRING, CZ CELLxGENE Census — each returning CURIE-tagged
  records, with local caching (respecting each source's redistribution license).
- Build the identifiers.org resolver integration so any CURIE can be dereferenced
  regardless of which connector produced it.
- Implement the license-gate wrapper for restricted sources (KEGG, BioCyc/EcoCyc, BiGG,
  BioNumbers, SABIO-RK) — off by default, enabled only with an explicit license
  acknowledgment per deployment.

**Exit criterion:** a query like "give me all annotated reactions for gene X" resolves
across at least 3 of the MVP sources and returns CURIE-linked, source-attributed data.

## Phase 4 — First real validated model

- Pick one small, extremely well-characterized subsystem — recommend *E. coli* core carbon
  metabolism or a single well-studied signaling pathway already in BioModels as a curated
  entry.
- Build it in Cradle's substrate, parameterize from BRENDA/SABIO-RK/literature with full
  STRENDA-style provenance, validate against the original publication's data.
- Run it through the curated/non-curated tiering process; mark it "curated" only once
  independently reproduced.
- Publish it as the first COMBINE archive artifact — this is Cradle's first real
  scientific output, not a demo.

**Exit criterion:** an external reviewer (or you, cold, a week later) can take the
published archive, re-run it on a different registered adapter, and reproduce the
original result without additional input.

## Phase 5 — AI layer v1

- Implement the 5 typed AI contracts (embedding, perturbation, sequence, structure,
  orchestration) as containerized, versioned adapters. **Note:** the perturbation contract
  here is v1 — the basic "baseline + spec → delta + uncertainty" shape. It gets extended
  with dose/curve, scalar-phenotype, and trajectory output modes in Phase 8, once real
  intervention data exposes what's missing.
- First models: Geneformer (embedding), Evo2 (sequence), OpenFold (structure — not AF3),
  TranscriptFormer (perturbation/cross-modal), Claude via MCP tool-calling (orchestration).
- Adopt LiteLLM for the orchestration layer's own provider routing.
- Conformance tests per contract (fixed input → schema-valid output + provenance).

**Exit criterion:** the orchestration agent can, given a natural-language question about
the Phase 4 model, call the embedding/structure contracts as tools and return an answer
with correct tool-call provenance logged.

## Phase 6 — Uncertainty & credibility hardening

- Wire profile-likelihood (COPASI) or SBI/ABC posteriors into every parameter-fitting path
  as a first-class, non-optional output.
- Enforce curated/non-curated labeling in every UI surface and export.
- Benchmark whatever AI-layer predictions exist against VCBench / Virtual Cell Challenge
  tasks; publish the score, including where it loses to the naive baseline.
- FAIR4RS self-assessment (`howfairis` or ARDC checklist) and first tagged release with a
  Zenodo DOI.

**Exit criterion:** every model in the system reports an uncertainty/identifiability
diagnostic alongside any fitted parameter, and there's a public benchmark number (even a
mediocre one) for the AI layer.

## Phase 7 — Molecular & regulatory tiers

Added after re-checking the roadmap against the project's full mission statement — gene
regulation and molecular interaction were previously only implicit, and a molecular-
dynamics tier was missing entirely.

- Define Cradle's own MD-tier contract (topology + force-field + integrator manifest in,
  H5MD trajectory out — no BioSimulators-equivalent registry exists for this yet). Wrap
  **OpenMM** (MIT/LGPL, native Python API) as the default adapter; prioritize
  MARTINI-class coarse-grained runs over full atomistic MD, since the latter is
  intractable at whole-cell scale.
- Add the **network inference** AI contract (expression + optional accessibility/motif
  priors → weighted TF→target graph + provenance). Wrap **pySCENIC + GRNBoost2** (GPL —
  isolate) as the default. Add **RegulonDB, CollecTRI, JASPAR** as Layer 6 data connectors
  for curated regulatory networks and motif priors.
- Add **SBML `qual`** as a model-definition package alongside SBML core (Layer 1), for
  Boolean/qualitative gene-regulatory models authored in **GINsim**/**BoolNet**. Write a
  custom (non-BioSimulators) execution adapter, since no mature registered logical-
  simulation engine exists.
- Add the **molecular interaction predictor** AI contract (2+ entities with roles +
  optional binding-site constraints → ranked complex poses + interface confidence +
  binding affinity). Wrap **OpenFold3** (co-folding), **Boltz-2** (structure+affinity,
  MIT), and **AutoDock Vina** (classical docking, Apache-2.0) as the three defaults.

**Exit criterion:** one working, conformance-passing adapter per new contract — a
coarse-grained MD run on a toy membrane/protein system, a GRN inferred from a toy
expression matrix and checked against a RegulonDB-known interaction, and a docking
prediction for a toy ligand-protein pair with a plausible pose and affinity score.

## Phase 8 — Intervention validation & perturbation-contract extension

Validates the platform against the four intervention types named in the mission statement
(drugs, gene edits, environmental stress, aging-related damage) — and, in doing so, forces
the Phase 5 perturbation contract to grow up from one generic shape into the several
shapes real data actually needs.

- Extend the perturbation-predictor contract with a `kind` field selecting output shape:
  vector delta (existing), scalar phenotype, dose/time curve, or age-indexed trajectory.
  Existing Phase 5 implementations that only support the vector-delta shape keep working
  unchanged — this is an additive extension, not a breaking one.
- **Gene edits** (best-fitting category): validate against **scPerturb** and
  **CRISPRbrain** using the existing vector-delta shape.
- **Gene-fitness screens**: validate the new scalar-phenotype mode against **DepMap
  Achilles** — ⚠ eval/benchmark only, its license forbids using it to train or enhance ML
  models; enforce this at the connector level (Phase 3's license-gate mechanism, extended
  with a `training_eligible` flag).
- **Drugs**: validate the new dose/curve mode against **LINCS L1000/CMap** and **ChEMBL**.
- **Environmental stress**: validate the new intensity/pathway-summary mode against
  **ASTRA** (⚠ CC BY-NC 4.0 — gate as non-commercial-only, and expect this to remain the
  thinnest-covered category — no single-cell-scale resource exists yet).
- **Aging**: validate the new trajectory mode against **Tabula Muris Senis** (already in
  CZ CELLxGENE Census from Phase 3 — no new connector needed).

**Exit criterion:** at least one real, non-toy case per intervention category runs through
the extended contract end to end and produces output in the correct shape for that
category, with the DepMap/ASTRA license gates demonstrably enforced (not just documented).

## Phase 9 — Spatial/multicellular expansion

- Add the custom "spatial experiment" archive format (Phase 0-defined pattern extended).
- Wrap **CompuCell3D** as the first spatial adapter (MIT, headless Python API).
- Add **PhysiCell** for higher-fidelity agent-based tissue modeling.
- Add **Smoldyn** (preferred) or **E-Cell4** (GPL — container-isolated) for particle-based
  spatial stochastic signaling.

**Exit criterion:** a spatial version of a Phase 4-class model (or a new small one) runs on
CompuCell3D and produces a result checkable against a known qualitative behavior
(e.g. a morphogen gradient, a growth pattern).

## Phase 10 — Visualization & interactive exploration

Closes the biggest gap found when checking the roadmap against the mission statement: an
interactive visual layer for exploring the cell from whole-cell behavior down to molecular
events, applying perturbations, and comparing alternative futures. No existing open-source
tool does this end to end — Cradle builds the compositing layer and reuses renderers.

- Register **Mol\*** (molecular), **Cytoscape.js** + optional **Escher** (pathway/network),
  **Simularium** (spatial/agent-based, with existing PhysiCell converters), and **VTK.js**
  (volumetric fields) as swappable Layer 10 renderer plugins, each activating at its own
  scale band.
- Build the scale-router: a shared-state, linked-view coordination layer modeled on
  **Vitessce**'s pattern, subscribing to the CURIE-addressed Layer 6 data so any renderer
  can be swapped without touching the router.
- Build scenario comparison as **small multiples**: N synchronized renderer instances, each
  bound to a different run's output, sharing one camera/time-slider controller.

**Exit criterion:** a user can view one validated model (from Phase 4 or later) rendered at
two different scales through the same linked-view state (e.g. pathway network zooming into
a molecular structure), and view two simulation runs side by side under one shared
time-slider.

## Phase 11 — Lab-facing interface & orchestration

- Jupyter-native API + widgets as the primary programmatic interface, complementary to the
  Phase 10 visual explorer (both read the same CURIE-addressed data; neither is secondary).
- CWL pipeline definitions for common multi-step workflows (fit → validate → simulate →
  benchmark), executable via Nextflow or Snakemake.
- Apptainer packaging for HPC/cluster deployment; Docker for local/cloud.
- ELN/LIMS-friendly export format for all results (structured, timestamped, provenance-
  complete COMBINE archives).

**Exit criterion:** someone outside the core team (ideally an actual lab collaborator) runs
a full fit-to-simulate workflow from a notebook without reading the source code, and the
output is something they'd trust enough to put in a lab notebook.

## Phase 12 — Second-wave AI models & governance maturity

- Add license-gated adapters for Arc State, ESM3/ESM C, AlphaFold3, AlphaFold-Multimer
  (all non-commercial deployments only), plus **SCENIC+**, **CellOracle**, and **HADDOCK**
  (non-commercial-academic licenses) — each requiring explicit legal sign-off before
  activation. Offer **NAMD** and **ChimeraX** as optional bring-your-own-license bridges
  for academic-only deployments, never bundled defaults.
- Formalize the community plugin-contribution process (contract spec + conformance suite
  + semver policy, documented for outside contributors).
- Revisit every "first implementation" choice from Phases 2/5/7/9/10 against whatever the
  state of the art has become — this phase should recur indefinitely, not close.

**Exit criterion:** an external contributor successfully adds a new adapter (data,
simulation, AI, or visualization) using only the published contract spec, with no direct
help from the core team.
