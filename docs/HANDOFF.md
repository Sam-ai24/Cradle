# Cradle — Session Handoff

**Last updated:** 2026-09-13 (E. coli essentiality flagship: iML1515 FBA × PEC × STRING
on a Mac, plus citation metadata and a first Docker build). Previous note:
**2026-08-27** (Phases 0-10 were built 2026-08-20 in one continuous run;
Phases 11 and 12, plus a genome-scale validation pass and a strategic landscape review, were
all built 2026-08-21; a further session spanning 2026-08-25 to 2026-08-27 built the GEARS
perturbation adapter, then — after strong user feedback that the Phase 10 visualization was
too thin a demo — rebuilt it into a general-purpose "Explorer" app over the whole plugin
registry, plus a reliability/test/docs pass. See entries 11-17 below).

This file is the single "start here" document for picking the project back up. It doesn't
duplicate `docs/ROADMAP.md` (the phase-by-phase build plan and detailed exit-criterion
verdicts), `README.md` (the project pitch + status summary), or `docs/LANDSCAPE.md` (how
Cradle compares to the real competitive landscape and what "scientific grade" requires) —
it records what a new session needs to *do* next and any operational detail that isn't
obvious from the code.

## What Cradle is (one paragraph)

An open, modular, scientifically-rigorous cell-simulation platform: every data source,
simulation engine, submodel, and AI model is a swappable plugin behind a versioned contract
(SBML/SED-ML/COMBINE for kinetic models, a custom manifest+H5MD contract for MD, a custom
manifest for spatial, SBML-qual for Boolean networks, typed AI contracts, CURIEs for data,
Python `entry_points` for plugin discovery). No layer ever calls another engine directly.
AI features (LLM orchestration) are fully optional and degrade gracefully with no key set.

## Standing constraints (do not violate these without the user explicitly changing them)

- **No Claude Artifacts.** All deliverables — docs, data, viz pages — are files inside this
  repo. Public GitHub (`https://github.com/Sam-ai24/Cradle`) was an explicit 2026-09-13
  week-1 decision; that does not mean shipping results via Claude Artifacts.
- **No fabricated results.** Every claim is checked against a real API, library, or dataset
  before being written down. Genuine blockers (missing package, no wheel, GPL isolation
  requirement, no discoverable REST API, native crash) are documented as blockers, not
  silently faked or skipped.
- **Commit at the end of each phase**, one commit per phase, with a detailed message
  (what was built, what was verified and how, any real bugs found/fixed). See `git log` for
  the exact style to match.
- **AI/API keys are opt-in.** Nothing in Cradle requires `ANTHROPIC_API_KEY` /
  `OPENROUTER_API_KEY` / `CRADLE_BIOGRID_API_KEY` to install or for non-AI features to work;
  their absence must always produce a clear `NotConfiguredError` skip, never a crash.

## Current state (2026-09-13)

Ported to macOS (`/Users/sam/Desktop/Projects/Cradle`, Python 3.11 venv). Flagship
question executed for real:

- iML1515 FBA single-gene deletion (1,516 genes, WT 0.877/h) vs PEC essentiality vs
  STRING v12 degree (taxon 511145).
- FBA vs PEC: MCC 0.57, AUROC 0.87, accuracy 0.92 (TP 93 / FP 102 / TN 1294 / FN 26).
- STRING hub baseline vs PEC: MCC 0.11, AUROC 0.63 — FBA wins.
- `folA` is PEC-essential and FBA-nonessential (isozyme `folM`), as previously documented.
- UniProt KW-0256 returned **zero** reviewed E. coli K-12 entries (live check); PEC
  `PECData.dat` is the literature layer instead.
- GEARS/DepMap were **not** used: wrong organism (human).
- cobra `single_gene_deletion` in 0.29+ stores gene ids in an `ids` column with a
  RangeIndex — worker was extended to read that, after a first run silently joined
  nothing (gene ids `"0"`, `"1"`, …).
- Citation: `CITATION.cff` / `codemeta.json` filled (Saman Bahadoran).
- Artifacts: `models/ecoli_flagship/`, `notebooks/ecoli_essentiality.ipynb`.

GEARS training is still untrained and still the wrong tool for this flagship; start it
only as a separate human-perturbation track, not as E. coli essentiality.

## Current state (2026-08-27)

| Phase | Status | Notes |
|---|---|---|
| 0 — Governance & scaffolding | ✅ done | plugin/conformance mechanism, 3 hello-world plugins |
| 1 — Model & experiment substrate | ✅ done | Antimony→SBML→SED-ML→COMBINE round-trip, toggle switch |
| 2 — First simulation adapters | ✅ done, validated at real scale 2026-08-21 | Tellurium, COPASI, COBRApy (subprocess-isolated); COBRApy also confirmed correct, unmodified, on a real genome-scale model (iML1515) |
| 3 — Knowledge/data layer | ✅ done | 7 live connectors + KEGG license gate; BioGRID needs a free key |
| 4 — First validated model | ✅ done | Repressilator (BIOMD0000000012), published to `models/repressilator/` |
| 5 — AI layer v1 | 🟡 partial | orchestration done; embedding done (`esmc_embedding` + `geneformer_embedding`, Phase 12); perturbation has a real adapter (`perturbation_gears`, GEARS/GNN) but **not yet trained** — a training run was interrupted with no checkpoint saved, see entry 11; sequence (Evo2) and structure (OpenFold) models still not built |
| 6 — Uncertainty & credibility | 🟡 mostly done | Wald CIs, tamper-resistant curation tier, HTTP retry; VCBench + tagged release blocked |
| 7 — Molecular & regulatory tiers | 🟡 3/4 done | MD (OpenMM), GRN inference (sklearn), SBML-qual done; docking blocked (no Vina wheel) |
| 8 — Intervention validation | 🟡 3/4 done | drugs/gene-fitness/gene-edits/aging done with real data; environmental stress (ASTRA) blocked (no REST API) |
| 9 — Spatial/multicellular | ✅ done | E-Cell4 (after CompuCell3D/PhysiCell/Smoldyn all ruled out) |
| 10 — Visualization | ✅ done, substantially expanded 2026-08-27 | Original repressilator scale-router generalized (comparison panel is now live/any-registered-engine/any-species, not 2 hardcoded engines showing 1 hardcoded species). Added a second page, `viz/explorer.html` + a real FastAPI backend (`viz/server.py`), exposing every registered plugin through generic panels (data search, AI predict, sim run, cross-engine compare, session history) plus a Network panel that derives a real species/reaction graph from any model's own SBML with no curation step, including live AlphaFold structure proxying. Escher/Simularium/VTK.js renderers still not built (no spatial/volumetric data to feed them yet) |
| 11 — Lab-facing interface | 🟡 3/4 done | `cradle.lab` notebook API + real executed notebook done; Snakemake pipeline runs, CWL written but `cwltool` doesn't run natively on Windows; Docker/Apptainer files written but unbuilt (no Docker/WSL2 here) |
| 12 — Second-wave AI & governance | 🟡 in progress | ESM-C-300M + Geneformer embedding adapters done (real, license-clean); CONTRIBUTING.md written + exit criterion verified via a fresh agent; 4/6 named second-wave models confirmed blocked/deferred; NAMD/ChimeraX bridge detection layer done, translation layer not attempted |

Full pytest suite as of the last commit: **98 passed, 6 skipped** (unconfigured keys/license
gates, plus the untrained GEARS model — all expected), **0 failed** on a normal run. (This
number keeps growing as more coverage is added — see entry 17 — not a sign anything shrank.)
Live-network tests (conformance, ChEMBL, CollecTRI) are known to flake under rate-limiting/
transient outages if the full suite is re-run repeatedly in a short window, or if a
third-party host has a bad moment (an EBI/ChEMBL HTTP 500 was seen live in an earlier
session) — unrelated to any Cradle code, and everything passes on a normal, isolated run.
The genome-scale FBA test (`tests/test_genome_scale_fba.py`) downloads an ~11MB model on
first run (cached after via `cradle.knowledge.cache`) and takes ~70-80s per run either way
(model parsing, not network, dominates) — don't be alarmed if the suite runs noticeably
longer than the ~6.5 minute warm-cache figure below on a cold cache.

## What just happened in this session (chronological)

1. Created the project at `C:\Users\bahad\Cradle`; did deep research (whole-cell models,
   CZI Virtual Cells Platform, what "scientific grade" requires) before writing any code.
2. Designed the layered swappable architecture (`docs/ARCHITECTURE.md`) and the phased
   roadmap (`docs/ROADMAP.md`), per explicit instruction to make Claude and OpenRouter both
   optional AI backends with graceful no-key degradation.
3. Built Phases 0-9 sequentially, one user "go with Phase N" at a time, each phase ending in
   real verification (live API calls, real datasets, actual physics/statistics checks) and
   a git commit. Real blockers hit and documented rather than faked: BioGRID/KEGG need
   registration or license ack; Evo2/OpenFold/Geneformer/TranscriptFormer need real
   GPU-scale weights (deferred); AutoDock Vina has no Windows wheel (deferred); ASTRA and
   RegulonDB have no discoverable REST API (deferred); CompuCell3D/PhysiCell have no PyPI
   path and Smoldyn segfaults on this build (E-Cell4 substituted, verified against exact
   diffusion physics).
4. Built Phase 10 (this session's last active work): `scripts/export_visualization_data.py`
   exports real Cradle data (the repressilator's real CURIEs/edges, real AlphaFold
   structures, real Tellurium/COPASI trajectories) into `viz/data/`; `viz/index.html` +
   `style.css` + `app.js` is a Cytoscape.js + Mol* scale-router with a shared time-slider
   comparison view. Found and fixed two real bugs along the way (AlphaFold 404 for one of
   three proteins; no CORS header on AlphaFold's file server — worked around by downloading
   structures server-side). Verified end-to-end in a live Chrome browser via
   `claude-in-chrome` (correct render, correct structure load + pLDDT, correct
   no-structure message, synced slider, zero console errors).
5. Closed out Phase 10: added `tests/test_visualization_export.py` (checks the export
   script's output against the model's own real CURIEs/edges, not hardcoded expectations,
   plus both engines' trajectory shapes), ran the full suite (51 passed, 2 skipped, 0
   failed), updated `docs/ROADMAP.md` and `README.md` with the real, honest Phase 10 outcome
   (including the two bugs and the three deferred renderers), and committed everything as
   `2e24d00`. Then wrapped the session: wrote this handoff doc, linked it from README, and
   added a memory pointer for future sessions.
6. Built Phase 11 (this session, 2026-08-21): `cradle.lab` (`api.py`/`report.py`/`widgets.py`)
   is the notebook-facing API; `notebooks/phase11_lab_workflow.ipynb` is a real, executed
   fit → validate → apply → simulate → benchmark → curate → report notebook (built + run by
   `scripts/lab_pipeline/build_notebook.py` via `nbclient`, outputs baked in). Found and fixed
   a real bug: COPASI's fitted-parameter name comes back as `"Values[alpha1].InitialValue"`,
   not the bare `"Values[alpha1]"` its own input uses — caught only because
   `apply_fitted_parameters` actually round-trips a real fit, not just checks the value.
   Wrote `workflows/lab_pipeline.cwl` (real, valid CWL) and four CLI scripts under
   `scripts/lab_pipeline/`; discovered `cwltool` doesn't run natively on Windows via two
   concrete errors (an unconditional `import pwd` crash in its Singularity-client dependency,
   then a `WinError 1314` needing a Windows privilege a normal account doesn't hold) rather
   than assuming it from cwltool's own "Windows unsupported" warning. Built
   `workflows/Snakefile` as the equivalent pipeline that actually runs here (verified by
   `tests/test_lab_pipeline.py` invoking it as a real subprocess). Wrote `Dockerfile` and
   `Apptainer.def` but left them explicitly unbuilt/unverified — no Docker Desktop or WSL2 on
   this machine, confirmed directly, not assumed. Ran the full suite (60 passed, 1 skipped, 0
   failed on a clean run — one live-network conformance test flaked under rate-limiting from
   repeated re-runs, unrelated to Phase 11), updated `docs/ROADMAP.md`/`README.md`/this file,
   and committed.
7. Built Phase 12 (this session, 2026-08-21, same day as Phase 11 but a separate session):
   checked feasibility of all six roadmap-named second-wave AI/tools directly rather than
   assumed — **CellOracle** (blocked: `velocyto`→`pysam` needs a Unix build toolchain),
   **HADDOCK3** (blocked: its `gdock` dependency's Rust extension fails to link with this
   machine's MSVC), **SCENIC+** (blocked: no PyPI package, unchanged from Phase 7), **Arc
   State** (installs cleanly, license genuinely is non-commercial, but its embedding
   checkpoint alone is 2.9-11GB and its more relevant model wants a training-run directory
   as input — deferred, not rushed), **AlphaFold3/-Multimer** (deferred: AF3 needs a manual
   DeepMind application regardless of any package, AF-Multimer needs TB-scale genetic
   databases) — leaving **ESM3/ESM-C**. Checking that one directly (rather than trusting the
   roadmap's own Phase-5-era assumption) found it's real, buildable: `HfApi().model_info(...)
   .gated` is `False` and the model's own `LICENSE.md` is plain MIT, contradicting
   `docs/ARCHITECTURE.md`/`NOTICE.md`'s prior "Cambrian Non-Commercial License" claim for
   this specific checkpoint — corrected both docs with a dated note. Built
   `plugins/esmc_embedding/` for real against ESM-C-300M (actual 1.3GB one-time download,
   ~110s first load/~8s cached, <2s CPU inference), proactively setting
   `HF_HUB_DISABLE_SYMLINKS=1` to avoid the same Windows-symlink-privilege class of bug Phase
   11 hit with cwltool. Built `cradle.lab.bridges` for NAMD/ChimeraX — the verifiable part
   (detect + run a configured executable) real and tested against a real binary (Python
   itself, standing in for the missing NAMD/ChimeraX); the config-translation part
   deliberately not attempted since it can't be tested here. Wrote `CONTRIBUTING.md`, then
   verified Phase 12's own exit criterion for real: launched a genuinely fresh agent with
   only `CONTRIBUTING.md`/`docs/ARCHITECTURE.md`/the contracts source (no access to any of
   Cradle's other real plugins) and had it build a new plugin unaided. It succeeded —
   `plugins/pubchem_data/`, a real PubChem connector, independently re-verified to pass
   `cradle-conformance` — and surfaced three real, now-fixed gaps in `CONTRIBUTING.md` (CURIE
   format wasn't stated in the connector section, what conformance actually asserts wasn't
   stated, and there was no pointer to `cradle.knowledge.http`'s retry helpers — left the
   fresh-built connector using raw `requests` rather than "fixing" it, since that would have
   hidden the gap the exercise was meant to find). Recheck of two old blockers (AutoDock
   Vina's Windows wheel, CompuCell3D's PyPI availability) found both unchanged. Ran the full
   suite (73 passed, 2 skipped, 0 failed), updated `docs/ROADMAP.md`/`README.md`/`Dockerfile`/
   `Apptainer.def`/this file, and committed.
8. Wrote `docs/LANDSCAPE.md` (real, web-researched comparison against Karr/Covert whole-cell
   models, CZI's Virtual Cells Platform, Arc Institute's Virtual Cell Challenge,
   VCell/CompuCell3D/PhysiCell, and single-cell foundation models — see that file for what
   it found and its own prioritized "what's needed for scientific grade" list). Then, per its
   own top recommendation, validated the **unmodified** `cobrapy` adapter against a real
   genome-scale model for the first time: iML1515 (Monk et al. 2017; 2,712 reactions, 1,516
   genes), fetched live from BiGG and cached via `cradle.knowledge.cache`. Correctly predicts
   the real ~0.877/h glucose-minimal-media growth rate and correctly classifies real
   essential (`murA`, `accA`) vs. non-essential (`lacZ`/`lacY`/`araA`) gene knockouts — the
   same in-silico-vs-real-biology validation style Karr et al. 2012 used. One real, kept
   (not hidden) nuance: a `folA` knockout is *not* lethal in this model, because of a real,
   independently documented redundant isozyme (`folM`) the model's own gene-reaction rule
   already annotates. `worker.py` gained one small, additive, backward-compatible extension
   (optional gene-knockout arguments) to support this. Updated `docs/ROADMAP.md` (Phase 2
   addendum), `README.md`, `docs/LANDSCAPE.md` (marked its own scale-demonstration item
   done), this file, and committed as `b5b4b46`.
9. Per `docs/LANDSCAPE.md`'s other top recommendation, built `plugins/geneformer_embedding/`
   — Geneformer, the single-cell embedding model `docs/ARCHITECTURE.md`'s own Layer 5 table
   has named as the intended default since Phase 5, never built until now. Not a licensing
   block (confirmed Apache-2.0, non-gated) but a genuinely multi-step install problem worked
   through rather than deferred: no PyPI package, a git clone of its HF repo failing with a
   real LFS partial-clone error, and its own `__init__.py` eagerly importing three submodules
   that need an unbuildable Cython extension (`accumulation-tree`, no MSVC toolchain here).
   Fixed by fetching the real package source via `huggingface_hub.snapshot_download` (no git
   at all) into a sandboxed local cache with a minimal replacement `__init__.py` — same
   disclosed-workaround category as Phase 11's `pwd.py` stub. Verified against real 10x
   Genomics `pbmc3k` cells (`tests/test_geneformer_embedding.py`): real, deterministic,
   per-cell-distinct 256-dim embeddings. Updated `docs/ARCHITECTURE.md`, `NOTICE.md`,
   `docs/ROADMAP.md`, `README.md`, `docs/LANDSCAPE.md` (marked its embedding recommendation
   partially done — the perturbation contract and an actual public benchmark submission are
   still open), this file, and committed as `0c8cb2b`.
10. Ran a real, honest benchmark check for that Geneformer adapter
    (`scripts/geneformer_embedding/run_benchmark.py`): a stratified 292-cell sample from
    `pbmc3k`, matched by real barcode to `pbmc3k_processed()`'s real published cell-type
    labels. CZI's `cz-benchmarks`/`scib-metrics` was the first choice for scoring but its
    `jaxlib` dependency fails to import here (`DLL load failed... Application Control
    policy` — a real, different Windows blocker) — used plain `sklearn` (silhouette score +
    5-fold k-NN probe) instead. **Real result: Geneformer's embedding clearly beats PCA (the
    field's simplest baseline) at separating real cell types** — 88.0% vs. 23.6% k-NN
    accuracy, silhouette 0.194 vs. -0.004. `tests/test_geneformer_benchmark.py` re-runs the
    same real comparison and asserts the real margin. Results in
    `docs/geneformer_benchmark.json`. Updated `docs/ROADMAP.md`, `README.md`,
    `docs/LANDSCAPE.md`, this file, and committed as `2c096bd`.
11. Built the perturbation AI contract's first real adapter: `plugins/perturbation_gears/`
    wraps GEARS (Roman-Rodriguez et al. 2023, MIT license), a GNN that predicts a cell's
    transcriptional response to a gene knockout, trained on the real Norman et al. 2019
    Perturb-seq dataset (89,357 cells). Found and fixed two real, confirmed
    version-incompatibility bugs in GEARS' own code (scipy no longer accepts a pandas Series
    boolean mask; PyTorch's autograd no longer allows in-place mutation of a leaf tensor
    requiring grad) via an idempotent runtime patcher
    (`plugins/perturbation_gears/compat_patches.py`), not a one-off manual edit. Training
    turned out far more expensive than the embedding adapters: ~50-60 minutes/epoch on this
    CPU-only machine. **A 5-epoch training run was killed by something outside process
    control partway through epoch 3** (genuinely still improving: epoch 1 val MSE 0.0051,
    epoch 2 0.0038) — `train_and_evaluate.py` now checkpoints after every epoch, takes
    `--epochs` as a CLI arg, and auto-detects cuda/mps/cpu (`perturbation_gears/device.py`)
    so a restart on stronger hardware needs no code change. A *second* training attempt was
    started later in this session and also did not finish — as of this writing
    `~/.cradle/cache/gears_norman_model/` is still empty, so `gears`'s perturbation contract
    is real but genuinely untrained; see "Pending work" below. Committed as `f7bdd3c`.
12. Wrote `docs/USER_GUIDE.md` (a practical, copy-pasteable tour of every capability),
    checking every code snippet live rather than from memory — caught and fixed one real bug
    doing so: `resolve_all()` returns a dict keyed by connector name (each value either a
    normal record or an `{"error": ...}`), not the flat list the first draft assumed.
    Committed as `4faade4`. (This guide's Explorer section was rewritten again in entry 17
    below, once the Explorer existed.)
13. User asked about moving the whole project to a stronger Mac Mini to continue there.
    Packaged the repo as a portable, no-GitHub-remote-needed git bundle
    (`git bundle create ... --all`, verified with `git bundle verify`) as the transfer
    mechanism. User then reconsidered (no Claude Code set up on that machine yet) and asked
    to keep going on the original Windows machine instead — the bundle was never used. *(A
    leftover `Cradle.bundle` file still sits at `C:\Users\bahad\Cradle.bundle`, outside the
    repo — harmless, but nobody's cleaned it up; see "Pending work.")* Then ran and visually
    verified the existing Phase 10 visualization end-to-end in a live Chrome browser
    (structure loading, pLDDT display, synced dual-engine time-slider all confirmed working).
    In response, the user gave strong, explicit negative feedback: the repressilator-only
    fixed demo undersold what's actually registered (16 data connectors, 7 simulation
    adapters, 11 AI model adapters at the time) and they wanted a real, general-purpose
    interface, not a curated one-off — explicitly asking for hot-reload visibility into
    further changes and for the dev server to never be closed.
14. Built **Cradle Explorer v1** (`viz/explorer.html` + a new `viz/server.py`, a real FastAPI
    app, not a second static demo) directly on top of the plugin registry: `GET /api/plugins`
    for live inventory, `GET /api/data/resolve` (the same `resolve_all`), `GET`/`POST
    /api/ai/example|predict/{name}` and `/api/sim/example|run/{name}` using the same
    conformance fixtures `cradle.conformance` uses — including the cached genome-scale
    iML1515 model — plus FastAPI's own `/docs`/`/redoc` surfaced directly in the UI. Result
    rendering infers shape generically (trajectories → chart, long numeric arrays → sparkline,
    scalars → badges, `resolve_all`'s per-connector dict → match/no-match badges) rather than
    special-casing any one adapter. Found a real perf bug immediately — `discover()`
    reconstructing every plugin (including heavy ESM-C/Geneformer/GEARS imports) on every
    single request took 30-60s; fixed with a per-process plugin cache. Followed immediately
    by a cross-engine Compare panel (groups simulation adapters by `input_mode`, runs every
    one sharing a group against the same real model, in parallel, via the same API) and a
    session run history (every query kept and re-viewable instead of vanishing on the next
    run). Committed as `b633658`, `45c5576`, `5796c48`.
15. Kept expanding the Explorer through many rounds of live verification in a real Chrome
    browser, each round finding and fixing a genuine gap in how a real adapter's output
    rendered: per-connector data records became clickable instead of buried in raw JSON with
    inventory filters added (`5796c48`); short label+series shapes (e.g. an aging-trajectory
    adapter's age-bin data) got their own chart type (`e074e6f`); `grnboost2-style` turned out
    to have no `conformance_input` at all (its "Load real example" silently sent a
    `{"probe": true}` placeholder that crashed with a raw `KeyError`) — fixed with the same
    deterministic TF1/TF2/decoy dataset its own test suite validates against, and ranked-table
    rendering added for its edge-list output (`d521966`); dose-response-shaped parallel
    numeric arrays got a real log-scale X/Y chart, verified against aspirin's real IC50 curve
    (`516f3a4`); flat gene→number dicts (e.g. Perturb-seq deltas) got ranked tables instead of
    exploding into dozens of individual badges (`d22fbff`). Then, per explicit user request,
    a full visual redesign into a self-contained "instrument panel" look (IBM Plex Sans/Mono,
    a teal/graphite palette, dark-mode-capable, live stats strip, sticky nav with
    scroll-spy), plus one-click quickstart recipes, adapter-docstring tooltips, and
    Run-button busy states (`6d61e85`, then `1b4791c` after the user asked for bright/light to
    be the enforced default over automatic OS dark mode).
16. Per user request ("is the repressilator page meant for more than this?"), generalized its
    comparison panel from 2 hardcoded engines/1 hardcoded species reading a pre-baked JSON
    file into a fully live query against whatever `combine_archive` adapters are actually
    registered, letting the user pick any real species — `scripts/export_visualization_data.py`
    no longer exports trajectories at all, only the curated graph/structure data, which still
    needs real hand curation and doesn't generalize on its own (`0c73b95`). Then built the
    general counterpart the roadmap actually calls for: a Network panel that derives a real
    bipartite species/reaction graph directly from any adapter's own SBML (extracted from a
    COMBINE archive's `manifest.xml`, or read directly for a plain `sbml_path`) — verified
    against the repressilator (6 species, 12 reactions, all real) and against the genome-scale
    iML1515 model, where an *uncapped* version produced 1805 reaction nodes from one hub
    metabolite and hung the browser tab; fixed by capping reactions independently of species,
    both truncations honestly disclosed in the UI rather than silent. Added
    `GET /api/structure/{accession}` to proxy real AlphaFold structures through the server
    (avoiding the direct-browser CORS failure the original export script's own docstring had
    already documented), verified live loading LacI's real structure into Mol* (`7c0cc10`).
    Along the way, found and fixed two real, previously-undiagnosed bugs behind repeated
    "my edit isn't showing up" confusion this session: plain `StaticFiles` let the browser
    cache `viz/*.css`/`*.js` indefinitely with no revalidation (fixed with a `Cache-Control:
    no-store` override, `0c73b95`), and `uvicorn --reload`'s Windows multiprocessing reloader
    was confirmed to get stuck mid-restart — it logs "Reloading..." but the old worker process
    never actually gets replaced — fixed by replacing it with `scripts/run_explorer.ps1`,
    which uses `watchfiles`'s own CLI to do a plain kill/relaunch instead, filtered to `*.py`
    changes only (`a3fdb3c`).
17. Asked "what can we make better?", proposed a prioritized punch list, and per the user's
    choice tackled reliability first: added `tests/test_explorer_server.py` (15 tests) for
    the network-building/SBML-extraction/structure-proxy logic added in entry 16, which had
    zero coverage — inconsistent with the rest of this project. The new tests immediately
    caught a real bug: `identifiers.org` resolves both a legacy slash-style URI
    (`identifiers.org/uniprot/P03023`, what the repressilator's own model uses) and the newer
    recommended colon-style compact identifier (`identifiers.org/uniprot:P03023`, what this
    project's own `cradle.substrate.annotate.annotate_with_curie()` writes) for the same real
    accession — the structure-lookup code only recognized the first, so it would have silently
    failed to find a structure for any model (including ones built with Cradle's own
    annotation helper) using the other, more modern convention. Fixed to accept both. Also
    fixed `tests/test_visualization_export.py`, left broken since entry 16 deleted the
    function one of its tests called. Rewrote `docs/USER_GUIDE.md`'s Explorer section (still
    described the old single-page static-file workflow) and added a `[viz]` extras group to
    `pyproject.toml` (`fastapi`/`uvicorn`/`watchfiles` were installed but declared nowhere).
    Ran the full suite clean throughout. Committed as `636fc34`, `d9c5d7b`, and this handoff
    update.

## Pending work, in a reasonable priority order

See also `docs/LANDSCAPE.md`'s own priority list (§5, "where this is realistically headed")
for the strategic view — genome-scale FBA validation (its #2) is done, and its #1 (a real
trained AI model) is now two-thirds done (embedding: `esmc_embedding` +
`geneformer_embedding`; perturbation has a real, tested, but untrained adapter — see #1
below; an actual public benchmark submission is still open). Its remaining items (the
public-release decision, a real external user) overlap with and motivate several of the
roadmap items below.

1. **Decide what to do about GEARS training** (freshest open item): two separate training
   attempts have now been interrupted with no checkpoint saved — see entry 11 above.
   `scripts/perturbation_gears/train_and_evaluate.py` checkpoints after every epoch, so a
   third attempt won't lose more than ~50-60 minutes of progress next time, but on this
   CPU-only machine a full 5-epoch run is realistically several hours. Options worth putting
   to the user explicitly rather than assuming: (a) just restart it and let it run
   uninterrupted in the background for a whole session, (b) reduce `--epochs` to get *a*
   checkpoint sooner even if less accurate, or (c) revisit the earlier "move to stronger
   hardware" idea from entry 13 — Claude Code would need to actually be set up on that
   machine this time, which is what stopped it before.
2. **Escher/Simularium/VTK.js renderers still not built** (Phase 10's remaining item, unlike
   everything else touched this session): still blocked on there being real volumetric-field
   or spatial-simulation output to visualize. Simularium in particular becomes buildable once
   Phase 9's E-Cell4 particle-position output is exported in a format its converters accept.
3. **Small cleanup, not urgent**: a leftover `C:\Users\bahad\Cradle.bundle` (git bundle, ~repo
   size) sits outside the repo from the abandoned Mac Mini transfer (entry 13) — safe to
   delete once confirmed unneeded, just never actually removed.
4. **Phase 5 remainder**: sequence (Evo2) and structure (OpenFold) AI contracts still not
   built — real model weights and likely GPU-relevant compute, the largest remaining lift in
   that phase now that embedding is done and perturbation has a real (if untrained) adapter.
5. **Phase 6 tagged release**: blocked on two decisions only the user can make — (a) their
   real name/affiliation for `CITATION.cff`/`codemeta.json` (currently placeholders), and
   (b) whether/when this local-only repo goes public (a Zenodo DOI requires a public GitHub
   repo). Ask the user directly next time this comes up rather than assuming either.
6. **Phase 7 docking contract**: AutoDock Vina needs Boost + a Windows build, or a
   precompiled binary plus OpenBabel/Meeko for molecule prep — evaluate that materially
   bigger lift, or look for an alternative that has a clean Windows wheel.
7. **Phase 8 environmental stress (ASTRA)**: no discoverable REST API as of this session —
   worth a fresh check in case ASTRA's access model has changed, before ruling it out again.
8. **Phase 11 container build/test**: `Dockerfile` and `Apptainer.def` are written but never
   built or run — this machine has no Docker Desktop and no WSL2. On a machine (or CI runner)
   that has either, actually build and run them (`docker build -t cradle .` /
   `apptainer build cradle.sif Apptainer.def`, then run the test suite inside) to convert
   "written" into "verified." Not urgent, but the one Phase 11 item that's genuinely just
   waiting on an environment, not a design decision.
9. **Phase 11 CWL on a Linux/WSL runner** (optional): `workflows/lab_pipeline.cwl` is real and
   valid but unverified by an actual `cwltool` run (only Snakemake was confirmed to execute,
   on this Windows machine). If a Linux/WSL environment becomes available, running
   `cwltool workflows/lab_pipeline.cwl ...` there would close this out fully.
10. **Phase 12 remainder**: Arc State (needs a 3-11GB download plus a training-run-directory
    input for its more relevant model — worth a real attempt if there's appetite for the
    larger lift), CellOracle/HADDOCK3 (would need a working Unix build toolchain or Rust/MSVC
    linker fix respectively — likely means a Linux/WSL environment, not a Windows fix), NAMD/
    ChimeraX's actual config/scripting translation layer (needs the real binaries to test
    against, which this machine doesn't have). AlphaFold3/-Multimer/SCENIC+ are blocked for
    structural reasons (manual license application, TB-scale database infra, no PyPI package)
    unlikely to change soon — not worth re-checking again until there's a specific reason to.
11. **The "revisit" mandate is meant to recur, not close** — periodically re-check
    Phase 2/5/7/9/10/11's engine/tool choices against the state of the art at whatever future
    point this is picked up again, the same way an earlier revisit found ESM3/ESM-C's license
    had genuinely changed since Phase 5.

No other loose ends: nothing half-implemented or silently stubbed. Every "not done" item
above is a documented, confirmed blocker (see `docs/ROADMAP.md` for the specific evidence
behind each one), not a TODO that was skipped without checking.

## Operational notes for the next session

- Repo has no CI configured (local-only, no remote). `git log` is entirely local; there is
  no GitHub remote configured yet.
- Use the project's own venv, not a global Python: `.venv/Scripts/python.exe` (Windows;
  this session's global `python` resolves to an unrelated hermes-agent venv without pytest).
- Full suite: `.venv/Scripts/python.exe -m pytest -q` (or `pytest -q` after activating
  `.venv`). As of 2026-08-27: **98 passed, 6 skipped, 0 failed** (~6.5 min with warm model
  caches, ~12 min cold — the genome-scale FBA test alone adds ~70-80s, and Geneformer/ESM-C's
  first-ever run downloads real weights).
- **To run the Explorer** (see `docs/USER_GUIDE.md` §1 for the full tour): `pip install -e
  ".[viz]"` once, then `powershell -File scripts/run_explorer.ps1` from the repo root, then
  open `http://localhost:8743/explorer.html` (general registry tour) or `.../index.html`
  (repressilator-specific scale-router; run `python scripts/export_visualization_data.py`
  once first if `models/repressilator/` has changed — it only exports the curated
  graph/structure data now, not trajectories, which are fetched live).
- **The Explorer's plugin list is cached per-process and does NOT pick up a newly
  `pip install -e`d plugin without a restart** — editable installs only touch site-packages
  metadata (well, and a `*.egg-info` dir under the plugin's own `src/`, but no `.py` file),
  so `scripts/run_explorer.ps1`'s `--filter python` watcher won't trigger on install either.
  Restart the script manually after installing a new plugin.
- **`uvicorn --reload`'s own Windows reloader is unreliable — confirmed to get stuck
  mid-restart twice this session** (logs "Reloading..." but the old worker process is never
  actually replaced, verified via unchanged process creation timestamps). Use
  `scripts/run_explorer.ps1` instead (a plain `watchfiles` kill/relaunch), not
  `uvicorn --reload` directly, for any future work on `viz/server.py`.
- `viz/server.py`'s static-file mount sends `Cache-Control: no-store` deliberately
  (`NoCacheStaticFiles`) — the browser was confirmed to silently cache old `viz/*.css`/`*.js`
  indefinitely otherwise. If a browser still shows stale content after an edit despite that,
  it's almost certainly a pre-existing cache entry from before this fix; a hard refresh
  (Ctrl+Shift+R) resolves it, and it shouldn't recur going forward.
- GEARS training (`scripts/perturbation_gears/train_and_evaluate.py`) has now been
  interrupted twice by something outside process control, not a crash in the training code
  itself — both times with `~/.cradle/cache/gears_norman_model/` left empty. See "Pending
  work" #1 for options. Per-epoch checkpointing means a future attempt is safe to just
  restart; it won't silently lose more than the epoch in progress.
- GPL-licensed engines (COBRApy, E-Cell4) are subprocess-isolated via a `worker.py` +
  `python -m` pattern — keep new GPL dependencies on this same pattern, never a direct
  in-process import (see `NOTICE.md`).
- License-gated connectors (KEGG, DepMap) are off by default and gated per `NOTICE.md`'s
  terms — follow the same `LicenseGate`/`training_eligible` pattern for any new restricted
  source.
- Phase 11 added two optional extras: `pip install -e ".[lab]"` (ipywidgets/jupyterlab/
  matplotlib/nbformat/nbclient, for the notebook + widgets) and `pip install -e ".[pipelines]"`
  (Snakemake). Neither is required for core Cradle or for `cradle.lab.api`/`.report`.
- **`cwltool` does not run natively on this Windows machine** — use `workflows/Snakefile`
  (`snakemake -s workflows/Snakefile --cores 1`) for the actual fit→apply→simulate→benchmark
  pipeline; `workflows/lab_pipeline.cwl` is kept as a real, valid, but locally-unverified
  equivalent for a Linux/WSL/CI runner. If you need to re-diagnose `cwltool` on Windows, note
  that a throwaway `pwd.py` stub was added to `.venv/Lib/site-packages/` during Phase 11's
  investigation purely to get past its Singularity-client dependency's `import pwd` crash —
  it's gitignored (inside `.venv/`) and not a repo artifact; recreate it only if you need to
  re-confirm the *next* blocker (`WinError 1314`, a missing Windows symlink privilege) rather
  than assuming this session's finding is stale.
- Shell rules/scripts that invoke `python` as a bare command (e.g. inside `workflows/Snakefile`)
  resolve it via `sys.executable`, not PATH — this machine has more than one Python install on
  PATH, and the first one found is not this project's venv.
- `plugins/esmc_embedding/` sets `HF_HUB_DISABLE_SYMLINKS=1` itself before importing
  `huggingface_hub` — without it, the first (uncached) model load crashes on Windows the same
  way cwltool's file staging did (`WinError 1314`, missing symlink privilege). If you add
  another `huggingface_hub`-based plugin, set this the same way rather than rediscovering it.
- Before assuming any model/tool is license-gated or blocked, check directly — this session
  found a real, dated correction (ESM3/ESM-C's license) by not trusting the roadmap's own
  earlier assumption. `HfApi().model_info(repo_id).gated` and the model's own `LICENSE.md`/
  README are the authoritative sources, not a general impression from when the roadmap was
  first written.
- `plugins/pubchem_data/` was built by a fresh verification agent, not by the core session
  work — it's real, tested, and independently re-verified to pass conformance, but it uses
  raw `requests` instead of `cradle.knowledge.http`'s retry helpers (a known, deliberately
  undisturbed gap — see Phase 12 in `docs/ROADMAP.md`). Fine to leave as-is or fix later;
  don't be surprised it doesn't match every other connector's exact pattern.

## Exactly what to tell the next session

> Continue the Cradle project at `C:\Users\bahad\Cradle`. Read `docs/HANDOFF.md` first for
> full context (entries 11-17 and the "Pending work"/"Operational notes" sections are the
> freshest and most likely to matter), then `docs/ROADMAP.md` for phase detail and
> `docs/LANDSCAPE.md` for the strategic picture. Two things changed shape since the last
> time this doc was written: (1) the perturbation AI contract now has a real adapter
> (`plugins/perturbation_gears`, GEARS) but it's genuinely untrained — two training attempts
> were each interrupted by something outside process control, and nobody's decided yet
> whether to just restart it, shrink `--epochs`, or move it to stronger hardware; (2) the
> Phase 10 visualization was substantially rebuilt into two real pages after the user gave
> strong feedback that the original repressilator-only demo undersold the project — a
> general-purpose "Explorer" (`viz/explorer.html` + `viz/server.py`, a real FastAPI backend,
> run via `powershell -File scripts/run_explorer.ps1`) now sits over the whole plugin
> registry with live data/model/sim panels, an auto-generated SBML-derived network view, a
> cross-engine comparison panel, and session history, alongside the original repressilator
> scale-router (`index.html`), whose own comparison panel is now live rather than pre-baked.
> Both pages, and the reliability work behind them (a working dev-restart script, real
> `tests/test_explorer_server.py` coverage, a fixed `identifiers.org` URI-format bug),
> are verified and committed. See `docs/USER_GUIDE.md` §1 for how to actually open it.
>
> Pick a direction: decide the GEARS training question (Pending work #1 — probably worth
> asking the user directly, it's their call), Phase 5's other remaining AI contracts
> (sequence, structure), an actual public benchmark submission
> (`docs/LANDSCAPE.md`'s remaining top recommendation), Phase 7's docking contract, Phase 8's
> ASTRA connector, Phase 10's Escher/Simularium/VTK.js renderers (still genuinely blocked on
> there being spatial/volumetric data to feed them), Phase 11's container build-and-test on a
> machine with Docker or WSL2, Phase 12's remaining second-wave models (Arc State is the most
> promising if there's appetite for a large download), the public-release decision
> (`docs/LANDSCAPE.md` §3, blocked on the user), or a fresh "revisit" pass over earlier
> phases' engine/tool choices against whatever's changed since. Keep everything local (no
> Claude Artifacts for this project), verify every claim against a real API/library/dataset
> before writing it down — including re-checking old assumptions, not just new ones, the way
> this session's tests caught a real annotation-format bug on the first try — document
> genuine blockers honestly instead of faking or skipping them, and commit to git with a
> detailed message in the same style as the existing commits.
