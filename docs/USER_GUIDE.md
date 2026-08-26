# Using Cradle — a practical tour

This is the "what can I actually do with this" doc — copy-pasteable commands, grouped by
what you're trying to accomplish, not by architecture layer. For the technical design, see
`docs/ARCHITECTURE.md`; for build history and status, `docs/ROADMAP.md`/`docs/HANDOFF.md`;
for how this compares to the field, `docs/LANDSCAPE.md`.

**One-time setup**, from the repo root:

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows; .venv\Scripts\activate.bat on cmd
pip install -e ".[dev,demo,lab,pipelines]"
```

Individual capabilities below each need their own plugin installed too (`pip install -e
plugins/<name>`) — each section says which.

## 1. See it in a browser — the Explorer

Unlike everything else in this doc, the Explorer isn't a fixed script — it's a real FastAPI
app (`viz/server.py`) sitting directly on top of the plugin registry, so it shows whatever
you've actually pip-installed, nothing hardcoded. Install a representative handful of
plugins to get a real first tour (install more any time — `pip install -e plugins/<name>`
only updates site-packages metadata, not any file under `viz/`/`src/`/`plugins/`, so the
running server's own discovery cache won't see it until you restart the script below):

```bash
pip install -e ".[viz]"
pip install -e plugins/uniprot_data -e plugins/alphafold_data -e plugins/tellurium_sim \
  -e plugins/copasi_sim -e plugins/cobrapy_fba -e plugins/esmc_embedding \
  -e plugins/grn_inference
```

Start the backend (Windows; on macOS/Linux drop the `.ps1` wrapper and run the `uvicorn`
command it contains directly — see the comment at the top of `viz/server.py`):

```powershell
powershell -File scripts/run_explorer.ps1
```

This watches `viz/`, `src/`, and `plugins/` for `*.py` changes and restarts the process
automatically (deliberately not `uvicorn --reload`, whose own Windows reloader was found to
silently hang mid-restart during development — see the script's comments). Static
`viz/*.html|css|js` need no restart at all; they're served fresh on every request and just
need a browser refresh.

Open **`http://localhost:8743/explorer.html`** — the general-purpose tour:

- **Registry**: every connector/adapter/model actually installed right now, live from
  `GET /api/plugins`.
- **Data / Models / Simulation**: search real biological data, run a real AI model, run a
  real simulation — each panel loads a genuine conformance-fixture example, not a
  hand-invented one, and "Not configured" (e.g. no API key, no trained checkpoint yet) is
  shown as an honest yellow state, not an error.
- **Network**: derives a real species/reaction graph directly from any selected adapter's
  own SBML — no curation required, unlike the page below. Click a species node with a
  UniProt annotation to try loading its real AlphaFold structure.
- **Compare**: groups simulation adapters by `input_mode` and runs every one that shares a
  group against the same real model, so you can see independent engines agree (or not).
- **Log**: every query this session, kept and re-runnable, instead of vanishing the moment
  you run the next one.

The "Try one" buttons at the top run a real end-to-end example in one click if you'd rather
not think about CURIEs or input shapes yet.

Separately, **`http://localhost:8743/index.html`** is the original Phase 10 scale-router,
scoped to one model with real hand curation: a repressilator regulatory-network view linked
to real AlphaFold structures of its three proteins, plus a live (not pre-baked) comparison
across every registered `combine_archive` engine. It needs one extra one-time step for the
curated topology + downloaded structures:

```bash
python scripts/export_visualization_data.py      # one-time, ~30s
```

## 2. Run the full "fit → simulate → report" workflow

A real Jupyter notebook that fits a model parameter to noisy data, validates the
uncertainty is honest, applies the fit, simulates on two independent engines, and exports a
lab-report Markdown file — using only high-level `cradle.lab` calls, no internals.

```bash
pip install -e plugins/tellurium_sim -e plugins/copasi_sim
jupyter lab notebooks/phase11_lab_workflow.ipynb
```

Already executed once with real outputs baked in — open it to read the result without
running anything, or re-run all cells yourself (Kernel → Restart & Run All) to reproduce it
live. Same pipeline is also runnable as a batch job, no notebook needed:

```bash
pip install -e plugins/perturbation_baselines   # not required, just an example env
python scripts/lab_pipeline/prepare_example_inputs.py
snakemake -s workflows/Snakefile --cores 1
cat workflows/example_output/benchmark.json      # real cross-engine agreement number
```

## 3. Query real biological data — one interface, many sources

`cradle.knowledge.router` fans one query out across every registered connector that can
answer it. Real, live APIs — nothing mocked.

```bash
pip install -e plugins/uniprot_data -e plugins/pdb_data -e plugins/reactome_data \
  -e plugins/biomodels_data -e plugins/string_data -e plugins/pubchem_data
```

```python
from cradle.knowledge.router import resolve_all
for connector_name, record in resolve_all("uniprot:P04637").items():   # TP53
    if "error" in record:
        print(connector_name, "-> skipped:", record["error"])   # e.g. no API key, or CURIE it can't answer
    else:
        print(connector_name, "->", record["source"], "->", record["data"])
```

Individual connectors also work directly — `plugins/pubchem_data` for compounds,
`plugins/chembl_data` for dose-response, `plugins/depmap_data` for gene-fitness screens,
`plugins/scperturb_data` for real Perturb-seq records, `plugins/aging_expression_data` and
`plugins/cellxgene_data` for single-cell atlas data. `kegg_data` is license-gated (off by
default — see `NOTICE.md` before enabling it).

## 4. Get a real protein or single-cell embedding

Two independent, real, trained embedding models — genuinely different domains.

```bash
pip install -e plugins/esmc_embedding
```

```python
from cradle.registry import discover
adapter = next(p.instance for p in discover("ai_model_adapter") if p.entry_point_name == "esmc")
result = adapter.predict({"curie": "uniprot:P0CG47"})   # or {"sequence": "MQIFV..."}
print(result["output"]["embedding_dim"], len(result["output"]["embedding"]))
```

For single-cell RNA-seq (real 10x Genomics PBMC data by default):

```bash
pip install -e plugins/geneformer_embedding
```

```python
adapter = next(p.instance for p in discover("ai_model_adapter") if p.entry_point_name == "geneformer")
result = adapter.predict({"h5ad_path": "your_real_counts.h5ad"})   # needs var["ensembl_id"], obs["n_counts"]
print(result["output"]["n_cells"], result["output"]["embedding_dim"])
```

First call downloads real weights (~1.3GB for ESM-C, a small ~40MB checkpoint for
Geneformer) and caches them under `~/.cradle/cache/` — one-time cost.

**Is it actually good?** Checked against the field's own simplest baseline (PCA) on real,
labeled PBMC data: Geneformer's embedding gets 88.0% vs. 23.6% 5-fold k-NN cell-type
accuracy. Full numbers in `docs/geneformer_benchmark.json`; re-run the comparison yourself
with `python scripts/geneformer_embedding/run_benchmark.py`.

## 5. Run a real genome-scale metabolic simulation

The same COBRApy adapter Phase 2 built for a 3-reaction toy network, unmodified, now proven
against a real *E. coli* genome-scale model (2,712 reactions, 1,516 genes).

```bash
pip install -e plugins/cobrapy_fba
```

```python
from cradle.knowledge.cache import cached_download
from cradle.registry import discover

path = cached_download("http://bigg.ucsd.edu/static/models/iML1515.xml")   # ~11MB, cached after first run
adapter = next(p.instance for p in discover("simulation_adapter") if p.entry_point_name == "cobrapy")

baseline = adapter.run({"sbml_path": str(path)}, {})
print("growth rate (1/h):", baseline["objective_value"])          # real: ~0.877

knockout = adapter.run({"sbml_path": str(path)}, {"gene_knockouts": ["b3189"]})  # murA
print("growth rate after murA knockout:", knockout["objective_value"])           # real: ~0.0 (essential gene)
```

Swap in any other real genome-scale model from the [BiGG database](http://bigg.ucsd.edu/models)
the same way — nothing about the adapter is specific to iML1515.

## 6. Predict a gene knockout's effect (perturbation contract)

**Status: not yet trained.** `plugins/perturbation_gears/` wraps a real GNN (GEARS) that
predicts a cell's transcriptional response to a gene knockout, trained on real Perturb-seq
data. A training attempt was interrupted with no checkpoint saved (training takes hours on
CPU); the per-epoch checkpointing in `scripts/perturbation_gears/train_and_evaluate.py`
means a restart won't lose more than one epoch's progress next time. See `docs/HANDOFF.md`
for the current state. Until a trained checkpoint exists, `predict()` raises a clear,
actionable error rather than fake output:

```bash
pip install -e plugins/perturbation_gears
```

```python
adapter = next(p.instance for p in discover("ai_model_adapter") if p.entry_point_name == "gears")
adapter.predict({"genes_to_perturb": ["KLF1"]})
# NotConfiguredError: 'gears' has no trained model yet - run
# 'python scripts/perturbation_gears/train_and_evaluate.py' first
```

For a working, real (if non-ML) alternative right now, `plugins/perturbation_baselines/`
gives real empirical lookups for four intervention types (drugs, gene-fitness, gene-edits,
aging) sourced from real ChEMBL/DepMap/scPerturb/Tabula Muris Senis data.

## 7. Ask a question in natural language (optional — needs your own API key)

```bash
pip install -e plugins/llm_orchestrator
export ANTHROPIC_API_KEY=sk-...        # or OPENROUTER_API_KEY
```

```python
adapter = next(p.instance for p in discover("ai_model_adapter") if p.entry_point_name == "claude")
result = adapter.predict({"task": "Summarize what the repressilator model does in one sentence."})
print(result["output"]["content"])
```

Cradle never ships or assumes a key of its own — without one, this reports a clear
"not configured" message instead of failing or silently doing nothing.

## 8. Add your own adapter

If none of the above does what you need, `CONTRIBUTING.md` is the complete, self-contained
guide — tested against a fresh agent with no other context, which built a working, real
`DataConnector` from that document alone. New data sources, simulation engines, and AI
models all register the same way (a Python package + an `entry_points` declaration), with
no change to Cradle's own code required.

## Where things stand right now

See `docs/HANDOFF.md` for the live phase-by-phase status and what's actively in progress —
GEARS training in particular may complete, need a restart, or need a different scope by the
time you read this.
