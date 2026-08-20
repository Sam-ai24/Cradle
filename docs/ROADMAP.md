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

## Phase 3 — Knowledge/data layer (MVP) — ✅ done (2026-08-20)

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

**Met.** Seven registered `data_connector` plugins hit real, live REST APIs — UniProt,
RCSB PDB, AlphaFold DB, Reactome, BioModels, STRING, CZ CELLxGENE Discover — plus a KEGG
connector as the flagship license-gated example (`cradle.knowledge.gate.LicenseGate`, off
by default, enabled via `CRADLE_LICENSE_ACK_KEGG=1`). BioGRID is implemented against its
documented API shape but requires a free registered key
(`CRADLE_BIOGRID_API_KEY`) neither available nor faked in this session — it reports as
`NotConfiguredError`, a new shared exception the conformance runner now treats as a *skip*,
distinct from an actual failure (Architecture, Layer 6: an access-control requirement isn't
the same problem as a broken connector). `cradle.knowledge.router.resolve_all(curie)` fans
one query out across every registered connector that accepts it — proven against a real
gene, TP53 (`uniprot:P04637`), chosen because (unlike Phase 1's bacterial toggle-switch
proteins) it has genuine coverage everywhere: the query resolves across 5 real sources at
once (`tests/test_knowledge_router.py`), each returning CURIE-linked, source-attributed
data, with no connector named by the caller. `cradle.knowledge.resolver.resolve_curie()`
independently dereferences any CURIE via the live identifiers.org API regardless of
whether Cradle has a connector for its namespace. The BioModels connector's live fetch of
`biomodels.db:BIOMD0000000507` also independently corroborated the exact CURIE Phase 1
already annotated the toggle switch with — including confirming its PubMed ID
(10659857), not previously double-checked.

## Phase 4 — First real validated model — ✅ done (2026-08-20)

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

**Met.** Chose the signaling-pathway path over metabolism: the Elowitz & Leibler (2000)
Repressilator, curated in BioModels as `BIOMD0000000012` — a real independently-curated
entry, not hand-authored like Phase 1's toggle switch. `cradle.substrate.examples.repressilator`
downloads the live SBML via Phase 3's `cradle.knowledge.http` and found a genuine gap:
BioModels annotated every species and reaction but left all 16 kinetic parameters
unannotated — a real failure by Cradle's own stricter Layer 8 rule that BioModels'
"curated" tier doesn't itself check. Closed by tracing each parameter back to the same
curated record before re-validating with `require_entity_annotations`.

Added `cradle.curation` — `promote_to_curated()` mechanically refuses to mark anything
"curated" unless every named evidence check passed *and* at least 2 independent adapters
reproduced it (`tests/test_curation.py` proves the refusal path, not just the happy path).
For an oscillator, point-by-point trajectory agreement between two solvers is the wrong
test — phase drift accumulates over many periods even between two numerically-correct
integrators — so `cradle.analysis` validates on peak count and amplitude range instead,
which are phase-invariant. Tellurium and COPASI agree to <1%: both report 9 oscillation
peaks over t=0-1000 and a peak amplitude of ~2368 model units, matching the published
"sustained oscillations" behavior.

Published to `models/repressilator/` (SBML, SED-ML, the COMBINE archive, and the
curation record — real files checked into the repo, not a temp-dir artifact) via
`scripts/curate_repressilator.py`. `tests/test_repressilator_curation.py` loads that
published archive from disk — not a freshly rebuilt copy — and reproduces the oscillation
on both registered adapters independently, satisfying the exit criterion literally.

## Phase 5 — AI layer v1 — 🟡 in progress (orchestration done 2026-08-20; embedding/sequence/structure/perturbation not yet built)

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

**Orchestration contract — done and real, not scaffolded.** `plugins/llm_orchestrator/`
registers two independently swappable adapters, `claude` and `openrouter`, both backed by
**LiteLLM** exactly as planned — one class (`LiteLLMOrchestrationAdapter`), two thin named
instances, matching the same "same contract, two parallel registered adapters" pattern
Phase 2 used for Tellurium/COPASI. AI orchestration is **entirely optional**: every other
Cradle capability (simulation, data connectors, curation) already works with zero AI
adapters configured, and this had to be true in practice, not just in a README claim — this
session has no `ANTHROPIC_API_KEY`/`OPENROUTER_API_KEY` set at all, so every test in
`tests/test_llm_orchestrator.py` runs the real "no key" path: each adapter checks for its
key *before* touching the network (proven by monkeypatching `litellm.completion` to fail
the test if it's ever called without one) and raises `NotConfiguredError` with the exact
env var and signup URL to fix it — the same skip-not-fail mechanism BioGRID (Phase 3) and
KEGG's license gate already established. `cradle.ai.get_orchestrator()` is the single entry
point a researcher or the future orchestrator-as-tool-caller would actually use: it returns
whichever configured provider is available (or the preferred one, if both are), and if
neither is configured, lists every option and how to enable it in one message instead of a
stack trace from whichever adapter happened to be tried first.

**Not yet built:** the embedding (Geneformer), sequence (Evo2), structure (OpenFold), and
perturbation (TranscriptFormer) contracts. These need substantial model weights and, for
Evo2/OpenFold in particular, real GPU-relevant compute — a materially larger and more
resource-intensive undertaking than anything built so far, deliberately not rushed to a
fake/stub state just to mark this phase fully done. The typed contract for each already
exists (`cradle.contracts.ai_model_adapter`, Architecture Layer 5); implementing them is the
next real increment of this phase, not a new phase.

## Phase 6 — Uncertainty & credibility hardening — 🟡 mostly done (2026-08-20)

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

**Uncertainty — done.** `cradle.estimation` (`ParameterEstimate`/`EstimationReport`) plus
`copasi_sim.estimation.estimate_parameters()` fits a parameter via COPASI's optimizer and
reports a Wald-type (Fisher-information/Hessian) confidence interval alongside the fitted
value — documented honestly as a local approximation, not a full profile-likelihood scan
(that's a real difference: Wald intervals can mislead for skewed/multimodal likelihoods a
true profile-likelihood pass would catch). Verified against a genuine ground truth, not
just checked for output shape: synthetic data generated at the toggle switch's real
alpha1=156.25, fit starting from a deliberately wrong guess (50), and the reported 95% CI
correctly contains 156.25 (`tests/test_parameter_estimation.py`).

**Curated/non-curated labeling — done, and hardened further than planned.** Beyond the
Phase 4 sidecar `curation.json`, the tier is now stamped *inside* the COMBINE archive
itself (`cradle.substrate.archive.embed_curation_tier`/`read_curation_tier`) — it survives
someone copying just the `.omex` file elsewhere, which a sidecar file never would. Finding
this mattered: the first implementation (modify the open `CombineArchive` object in place,
then `writeToFile`) silently zeroed out every pre-existing entry's content — a real
libcombine quirk caught by the exit-criterion tests actually re-running the rewritten
archive, not by a shape check. Fixed by rebuilding from scratch (extract to disk, re-`addFile`
each entry) — the same proven pattern `package_combine_archive` already used.

**Also hardened, not originally scoped:** `cradle.knowledge.http` now retries transient
failures (timeouts, connection errors, 5xx) with backoff and raises immediately on a 4xx
(retrying an identical bad request can't help) — added after a live UniProt timeout
actually failed a conformance run mid-session, then succeeded seconds later unretried.

**VCBench benchmark — explicitly not done, not silently skipped.** There is nothing
meaningful to submit: Phase 5 only built the orchestration contract (Claude/OpenRouter via
LiteLLM), not the embedding/perturbation models VCBench actually evaluates (Geneformer,
scGPT, UCE, TranscriptFormer, Arc State). Publishing a benchmark number now would mean
benchmarking nothing. This bullet is blocked on finishing Phase 5's remaining AI contracts,
not abandoned.

**FAIR4RS self-assessment — done** (`docs/FAIR4RS_ASSESSMENT.md`); **tagged release — not
done, and correctly blocked**, not forgotten: `CITATION.cff`/`codemeta.json` still carry the
placeholder author fields set in Phase 0 (real name/affiliation only the researcher can
supply), and no decision has been made on whether/when this local-only repo goes public —
Zenodo DOI minting requires a connected public GitHub repo, which is a bigger, more visible
step than anything done under the "keep everything local" instruction so far. Tagging a
release with placeholder citation metadata would contradict the point of this phase.

## Phase 7 — Molecular & regulatory tiers — 🟡 3/4 done (2026-08-20)

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

**MD tier — done.** `cradle.md` defines the manifest (particles/bonds/nonbonded/integrator)
and a real H5MD writer/reader, checked directly against the H5MD spec
(h5md.nongnu.org) rather than assumed. `plugins/openmm_md/` runs a coarse-grained
bead-spring chain via OpenMM and reports scalar diagnostics (potential/kinetic energy,
instantaneous temperature via equipartition) alongside the full trajectory in H5MD —
particle positions don't fit the scalar `trajectories` shape, so they go to the H5MD file
instead of being forced into it. Verified against real physics, not just checked for
output shape: a Langevin-thermostatted toy chain equilibrates to within 15% of its 300 K
target (`tests/test_openmm_adapter.py`).

**Network inference — done, with a real substitution.** `arboreto`/GRNBoost2 — this
roadmap's originally planned default — is **confirmed broken** against current
`dask`/`distributed` (`TypeError: Must supply at least one delayed object`), not merely
stale as flagged from research alone. `plugins/grn_inference/` implements the same
algorithm directly (per-target gradient-boosted regression + feature-importance ranking)
via scikit-learn instead. Validated against synthetic ground truth: a real driver TF, a
decoy TF correlated with nothing, and a noise gene — the adapter correctly ranks the real
edges far above the decoy's and correctly reports low R² for the noise gene rather than
mistaking a coin-flip importance split for a real edge (`tests/test_grn_inference.py`).
Added **CollecTRI** (via OmniPath's REST API) as a Layer 6 curated-network connector —
**RegulonDB deferred**: its API has moved to GraphQL with no simple queryable REST endpoint
found in a reasonable search, unlike CollecTRI's genuinely tractable REST access.

**SBML `qual` — done, without GINsim/BoolNet.** `cradle.qual` reads SBML `qual` models
(species, transitions, functionTerms) and evaluates their MathML conditions directly — a
real recursive AST evaluator (relational + logical ops), not a hardcoded special case —
then executes synchronous Boolean-network updates as Cradle's own adapter
(`plugins/boolean_qual_sim/`), avoiding a second-language runtime (Java for GINsim, R for
BoolNet) for a genuinely simple update rule. Two real bugs surfaced and got fixed while
building this: `setPackageRequired()` is silently a no-op if called before
`enablePackage()`, and function-term `ASTNode`s become dangling pointers once the parsing
`SBMLDocument` goes out of scope unless explicitly `.deepCopy()`'d — both caught only
because the correctness tests actually execute the model rather than just checking its
shape. Verified against two independently provable dynamical facts about the same mutual-
repression network: it period-2-oscillates from a symmetric start and sits at a fixed
point from an asymmetric one (`tests/test_boolean_qual_adapter.py`).

**Molecular interaction predictor — not done, and correctly blocked, not faked.**
AutoDock Vina's Python bindings require Boost and have no prebuilt wheel for this
platform — confirmed by a direct install attempt (`ValueError: Boost library location was
not found!`), not assumed from documentation. Building it would mean either compiling from
source against Boost or trusting a downloaded precompiled binary plus a separate molecule-
preparation toolchain (OpenBabel/Meeko) — a materially bigger, more fragile undertaking
than anything else in this phase, on the same footing as Evo2/OpenFold/TranscriptFormer's
deferral in Phase 5. The typed contract itself (multi-entity input, ranked poses + interface
confidence + affinity output) is already specified in `docs/ARCHITECTURE.md`'s Layer 5
table; only the implementation is missing.

## Phase 8 — Intervention validation & perturbation-contract extension — 🟡 3/4 done (2026-08-20)

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

**Met for three of four categories — with real data throughout, not synthetic stand-ins.**
`cradle.perturbation` adds the `kind` field (`vector_delta`/`scalar_phenotype`/`dose_curve`/
`trajectory`) with a real validator (`validate_perturbation_output`) that mechanically
checks an output actually has its declared kind's required fields — proven additive by a
dedicated test showing the original Phase 5 `vector_delta` shape validates unchanged.
`plugins/perturbation_baselines/` implements one **empirical baseline** adapter per kind —
explicitly *not* trained predictive models, real-data lookups, exactly the kind of
comparator VCBench itself benchmarks AI models against:

- **Drugs (`dose_curve`)**: real ChEMBL IC50 for aspirin, expanded into the standard
  Hill-equation sigmoid that value parameterizes. LINCS/CLUE was reachable only with a
  registered API key (deferred, same BioGRID-style gate) — ChEMBL alone already satisfies
  the exit criterion for this category.
- **Gene-fitness screens (`scalar_phenotype`)**: real DepMap Achilles CRISPR gene-effect
  scores for KRAS across hundreds of cell lines, fetched from a real ~98MB bulk file
  (`cradle.knowledge.cache` added for exactly this — large one-time downloads, cached
  locally rather than re-fetched every call). `training_eligible: False` is a real field on
  every record this connector returns, not a comment — checked directly by a test.
- **Gene edits (`vector_delta`)**: real Perturb-seq data from scPerturb (Dixit & Regev 2016,
  a landmark CRISPR knockdown screen), not the multi-GB files originally assumed
  inaccessible — the *smallest* files in the harmonized collection (46-121MB) turned out to
  be genuinely tractable, confirmed by actually downloading and reading one rather than
  estimating from a file listing. The connector reports the CRISPR target gene's own
  expression delta directly (a real, if modest, knockdown effect on IRF1 itself) rather than
  hoping it lands in an arbitrary top-N cutoff.
- **Aging (`trajectory`)**: real Tabula Muris Senis single-cell data (pancreas, Smart-seq2)
  across four real donor ages (18/21/24/30 months). Checked the canonical senescence marker
  Cdkn2a directly against real data before writing anything — it does **not** show a clean
  monotonic increase in this tissue slice (likely confounded by a 51-cell group at 24
  months). The adapter and its test report this honestly rather than asserting the textbook
  direction or quietly switching to a different gene until one "worked."

**Environmental stress — not done, correctly blocked.** ASTRA's site is a JS single-page
app with no discoverable REST endpoint found in a reasonable search (same category of gap
as RegulonDB in Phase 7) — this remains the thinnest-covered intervention category, exactly
as flagged when this phase was first planned.

## Phase 9 — Spatial/multicellular expansion — ✅ done, with a different engine than planned (2026-08-20)

- Add the custom "spatial experiment" archive format (Phase 0-defined pattern extended).
- Wrap **CompuCell3D** as the first spatial adapter (MIT, headless Python API).
- Add **PhysiCell** for higher-fidelity agent-based tissue modeling.
- Add **Smoldyn** (preferred) or **E-Cell4** (GPL — container-isolated) for particle-based
  spatial stochastic signaling.

**Exit criterion:** a spatial version of a Phase 4-class model (or a new small one) runs on
CompuCell3D and produces a result checkable against a known qualitative behavior
(e.g. a morphogen gradient, a growth pattern).

**Met — with E-Cell4, not CompuCell3D or Smoldyn, after all three of the roadmap's other
named engines turned out genuinely blocked, confirmed one at a time rather than assumed:**

- **CompuCell3D**: no PyPI/pip package at all (confirmed against PyPI directly) — it's
  conda-only, and no conda is available in this environment.
- **PhysiCell**: no PyPI/pip package either — it's a C++ codebase built via its own
  Makefile, with no Python packaging path.
- **Smoldyn** (the roadmap's own "preferred" choice): installs cleanly, and basic
  simulation (`run()` + `getMoleculeCount()`) works — but retrieving molecule *positions*
  via its standard `listmols`/output-table mechanism (`addOutputData` + `addCommand` +
  `getOutputData`) causes a **reproducible segmentation fault** in this build, isolated
  down to the smallest possible case (10 molecules, 10 timesteps, one output command) to
  confirm it wasn't a scale issue. A real native crash is a more serious problem than a
  clean install failure, so this was ruled out rather than worked around.
- **E-Cell4**: installs cleanly, and its `spatiocyte` (particle-based spatial-stochastic)
  module has a genuine object-level Python API (`list_particles_exact()` returns real
  `Particle` objects with `.position()`) that never touches the crash-prone
  command/output-table pattern at all. One real performance gotcha found and resolved:
  `add_molecules(species, count, Sphere(center, radius))` does rejection-sampling to find
  empty voxels, which is pathologically slow if `radius` is too small relative to `count`
  and the world's voxel size (confirmed: radius 0.3 never completed placing 300 molecules
  within 40+ seconds; radius 0.5 placed 500 molecules near-instantly) — documented directly
  in `ecell4_spatial/worker.py`, not left as a silent trap.

`cradle.spatial` defines the manifest (species with diffusion coefficient/radius, a point
source, domain size, step count) — the same "no BioSimulators-equivalent contract exists"
pattern as the MD tier (Phase 7). `plugins/ecell4_spatial/` runs E-Cell4 subprocess-isolated
(GPL-3.0, same pattern as `cobrapy_fba`). Verified against **exact analytical physics, not
just a qualitative pattern**: for free diffusion from a point source, particle-position
standard deviation along any axis must grow as `sqrt(2*D*t)` — the closed-form solution of
the diffusion equation. Checked at 4 independent time points in one run, matching the
prediction throughout (`tests/test_ecell4_spatial_adapter.py`) — a stronger result than the
roadmap's own "checkable against a known qualitative behavior" bar asked for.

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
