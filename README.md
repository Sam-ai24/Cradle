# Cradle

Cradle is a cell simulation platform built to be scientifically credible (traceable to
real data, validated, uncertainty-aware) and permanently upgradeable — every data source,
simulation engine, submodel, and AI model is a swappable, versioned component, so the
system keeps absorbing better science and better models instead of being rewritten for them.

## Documents

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

**Phase 2 (first simulation adapters) — done.** Three registered `SimulationAdapter`
plugins under `plugins/`: Tellurium/libRoadRunner and COPASI (both run the Phase 1 toggle
switch unmodified and agree numerically to within 0.1%) and COBRApy for FBA (subprocess-
isolated per its GPL/LGPL license, verified against an analytically obvious optimum on a
synthetic toy network). `cradle-conformance` now dispatches its check per adapter's
declared `input_mode`, so real archive-based adapters get checked against a real reference
archive while the Phase 0 toy plugin keeps passing unmodified.

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

## Getting started (local dev)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat on cmd
pip install -e ".[dev,demo]" \
  -e plugins/hello_data -e plugins/hello_sim -e plugins/hello_ai \
  -e plugins/tellurium_sim -e plugins/copasi_sim -e plugins/cobrapy_fba \
  -e plugins/uniprot_data -e plugins/pdb_data -e plugins/alphafold_data \
  -e plugins/reactome_data -e plugins/biomodels_data -e plugins/string_data \
  -e plugins/biogrid_data -e plugins/cellxgene_data -e plugins/kegg_data \
  -e plugins/llm_orchestrator

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
