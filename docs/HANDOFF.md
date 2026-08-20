# Cradle — Session Handoff

**Last updated:** 2026-08-21 (Phases 0-10 were built 2026-08-20 in one continuous run; Phase
11 was built 2026-08-21 in the following session).

This file is the single "start here" document for picking the project back up. It doesn't
duplicate `docs/ROADMAP.md` (the phase-by-phase build plan and detailed exit-criterion
verdicts) or `README.md` (the project pitch + status summary) — it records what a new
session needs to *do* next and any operational detail that isn't obvious from the code.

## What Cradle is (one paragraph)

An open, modular, scientifically-rigorous cell-simulation platform: every data source,
simulation engine, submodel, and AI model is a swappable plugin behind a versioned contract
(SBML/SED-ML/COMBINE for kinetic models, a custom manifest+H5MD contract for MD, a custom
manifest for spatial, SBML-qual for Boolean networks, typed AI contracts, CURIEs for data,
Python `entry_points` for plugin discovery). No layer ever calls another engine directly.
AI features (LLM orchestration) are fully optional and degrade gracefully with no key set.

## Standing constraints (do not violate these without the user explicitly changing them)

- **Local-only.** No Claude Artifacts for Cradle. All deliverables — docs, data, viz pages —
  are files inside this repo. (Saved to memory as `cradle-project-local-only.md`.)
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

## Current state (2026-08-21)

| Phase | Status | Notes |
|---|---|---|
| 0 — Governance & scaffolding | ✅ done | plugin/conformance mechanism, 3 hello-world plugins |
| 1 — Model & experiment substrate | ✅ done | Antimony→SBML→SED-ML→COMBINE round-trip, toggle switch |
| 2 — First simulation adapters | ✅ done | Tellurium, COPASI, COBRApy (subprocess-isolated) |
| 3 — Knowledge/data layer | ✅ done | 7 live connectors + KEGG license gate; BioGRID needs a free key |
| 4 — First validated model | ✅ done | Repressilator (BIOMD0000000012), published to `models/repressilator/` |
| 5 — AI layer v1 | 🟡 partial | orchestration (Claude/OpenRouter via LiteLLM) done; embedding/sequence/structure/perturbation models **not built** |
| 6 — Uncertainty & credibility | 🟡 mostly done | Wald CIs, tamper-resistant curation tier, HTTP retry; VCBench + tagged release blocked |
| 7 — Molecular & regulatory tiers | 🟡 3/4 done | MD (OpenMM), GRN inference (sklearn), SBML-qual done; docking blocked (no Vina wheel) |
| 8 — Intervention validation | 🟡 3/4 done | drugs/gene-fitness/gene-edits/aging done with real data; environmental stress (ASTRA) blocked (no REST API) |
| 9 — Spatial/multicellular | ✅ done | E-Cell4 (after CompuCell3D/PhysiCell/Smoldyn all ruled out) |
| 10 — Visualization | 🟡 core done | Cytoscape.js + Mol* scale-router, 2-way run comparison; Escher/Simularium/VTK.js not built (no data to feed them yet) |
| 11 — Lab-facing interface | 🟡 3/4 done | `cradle.lab` notebook API + real executed notebook done; Snakemake pipeline runs, CWL written but `cwltool` doesn't run natively on Windows; Docker/Apptainer files written but unbuilt (no Docker/WSL2 here) |
| 12 — Second-wave AI & governance | ⬜ not started | Arc State/ESM3/AlphaFold3/etc., community contribution process |

Full pytest suite as of the last commit: **60 passed, 1 skipped** (an unconfigured key/
license gate — expected), **0 failed** on a normal run. One live-network conformance test
(CollecTRI, against omnipathdb.org/reactome.org) is known to flake under rate-limiting if the
full suite is re-run repeatedly in a short window — unrelated to Phase 11's changes, and it
passes on a normal single run.

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

## Pending work, in a reasonable priority order

1. **Phase 5 remainder** (biggest open gap): implement the embedding (Geneformer), sequence
   (Evo2), structure (OpenFold), and perturbation (TranscriptFormer) AI contracts. This is
   the largest, most resource-intensive remaining item — real model weights and likely
   GPU-relevant compute. Unblocks the VCBench benchmark bullet in Phase 6.
2. **Phase 6 tagged release**: blocked on two decisions only the user can make — (a) their
   real name/affiliation for `CITATION.cff`/`codemeta.json` (currently placeholders), and
   (b) whether/when this local-only repo goes public (a Zenodo DOI requires a public GitHub
   repo). Ask the user directly next time this comes up rather than assuming either.
3. **Phase 7 docking contract**: AutoDock Vina needs Boost + a Windows build, or a
   precompiled binary plus OpenBabel/Meeko for molecule prep — evaluate that materially
   bigger lift, or look for an alternative that has a clean Windows wheel.
4. **Phase 8 environmental stress (ASTRA)**: no discoverable REST API as of this session —
   worth a fresh check in case ASTRA's access model has changed, before ruling it out again.
5. **Phase 10 remaining renderers** (Escher, Simularium, VTK.js): blocked on there being
   real volumetric-field or spatial-simulation output to visualize. Simularium in particular
   becomes buildable once Phase 9's E-Cell4 particle-position output is exported in a format
   Simularium's converters accept — worth scoping as a small follow-up to Phase 9/10 rather
   than waiting for a new phase.
6. **Phase 11 container build/test**: `Dockerfile` and `Apptainer.def` are written but never
   built or run — this machine has no Docker Desktop and no WSL2. On a machine (or CI runner)
   that has either, actually build and run them (`docker build -t cradle .` /
   `apptainer build cradle.sif Apptainer.def`, then run the test suite inside) to convert
   "written" into "verified." Not urgent, but the one Phase 11 item that's genuinely just
   waiting on an environment, not a design decision.
7. **Phase 11 CWL on a Linux/WSL runner** (optional): `workflows/lab_pipeline.cwl` is real and
   valid but unverified by an actual `cwltool` run (only Snakemake was confirmed to execute,
   on this Windows machine). If a Linux/WSL environment becomes available, running
   `cwltool workflows/lab_pipeline.cwl ...` there would close this out fully.
8. **Phase 12** (Arc State/ESM3/AlphaFold3/etc., community contribution process) — not
   started; also explicitly meant to recur (revisit Phase 2/5/7/9/10/11's engine/tool choices
   against the state of the art at that time).

No other loose ends: nothing half-implemented or silently stubbed. Every "not done" item
above is a documented, confirmed blocker (see `docs/ROADMAP.md` for the specific evidence
behind each one), not a TODO that was skipped without checking.

## Operational notes for the next session

- Repo has no CI configured (local-only, no remote). `git log` is entirely local; there is
  no GitHub remote configured yet.
- Use the project's own venv, not a global Python: `.venv/Scripts/python.exe` (Windows;
  this session's global `python` resolves to an unrelated hermes-agent venv without pytest).
- Full suite: `.venv/Scripts/python.exe -m pytest -q` (or `pytest -q` after activating
  `.venv`). Takes ~2 minutes; expect `51 passed, 2 skipped`.
- To view the Phase 10 visualization: `python scripts/export_visualization_data.py` (only
  needed again if `models/repressilator/` changes) then
  `python -m http.server 8743 --directory viz` and open `http://localhost:8743`. Already
  exported once — `viz/data/*.json` and `viz/data/structures/*.pdb` are committed.
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

## Exactly what to tell the next session

> Continue the Cradle project at `C:\Users\bahad\Cradle`. Read `docs/HANDOFF.md` first for
> full context, then `docs/ROADMAP.md` for phase detail. Phases 0-11 are built and committed
> (10 and 11 are each "partial, done" — see the table in HANDOFF.md for exactly what's
> partial and why). Go with Phase 12 [or: finish Phase 5's remaining AI contracts / Phase 7's
> docking contract / Phase 8's ASTRA connector / Phase 10's Simularium renderer / Phase 11's
> container build-and-test on a machine with Docker or WSL2 — pick whichever you want next].
> Keep everything local (no Claude Artifacts for this project), verify every claim against a
> real API/library/dataset before writing it down, document genuine blockers honestly instead
> of faking or skipping them, and commit to git at the end of the phase with a detailed
> message in the same style as the existing commits.
