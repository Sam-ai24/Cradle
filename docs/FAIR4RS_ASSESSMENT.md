# FAIR4RS Self-Assessment

A real assessment of Cradle against the [FAIR4RS Principles](https://ardc.edu.au/resource/fair-principles-for-research-software-fair4rs/)
(Findable, Accessible, Interoperable, Reusable — for research **software**,
not just its output data), as of 2026-08-20. Written to surface what's
actually missing, not to check a box — a "first tagged release" isn't
meaningful while some of these are still open.

## Findable

| Criterion | Status | Note |
|---|---|---|
| Persistent identifier (DOI) | ❌ Not done | No Zenodo release exists. Minting one requires a public GitHub repo connected to Zenodo — a real, semi-irreversible action tied to the researcher's own account, not something to do on their behalf without asking. |
| Rich, machine-readable metadata | 🟡 Partial | `CITATION.cff` and `codemeta.json` exist with the right structure, but both still carry the placeholder author fields (`"TODO"` / `"TODO — fill in your name here"`) set when they were first created in Phase 0. **This is a real, unresolved gap, not a formality** — citation metadata with a placeholder name is arguably worse than none, since it looks real at a glance. |
| Registered/indexed somewhere findable | ❌ Not done | Repository is local-only (per project instruction); not on GitHub or any registry yet. |

## Accessible

| Criterion | Status | Note |
|---|---|---|
| Retrievable by identifier | ❌ Not applicable yet | No public URL exists to retrieve it from. |
| Metadata accessible even if software isn't | ❌ Not applicable yet | Same reason. |

## Interoperable

| Criterion | Status | Note |
|---|---|---|
| Uses community standards for data/model exchange | ✅ Done | SBML, SED-ML, COMBINE/OMEX throughout (Layers 1-3); every data-layer entity is a CURIE resolved through identifiers.org (Layer 6). This is the strongest category — it was designed in from Phase 1, not retrofitted. |
| Machine-readable interfaces | ✅ Done | Python `entry_points`-based plugin contracts (`DataConnector`, `SimulationAdapter`, `AIModelAdapter`), each conformance-tested. |

## Reusable

| Criterion | Status | Note |
|---|---|---|
| Clear, OSI-approved license | ✅ Done | Apache-2.0 (`LICENSE`), with `NOTICE.md` documenting every third-party license constraint found across five phases of research (GPL isolation requirements, KEGG/BioCyc/AlphaFold3/DepMap restrictions, etc.) — this is more thorough than the bare minimum "has a LICENSE file" bar. |
| Documented dependencies | ✅ Done | Every plugin package declares its own `pyproject.toml` dependencies; `docs/RESOURCES.md` documents licensing/maintenance status for everything considered, not just what was adopted. |
| Quality checks / tests | ✅ Done | 35 tests as of this phase, covering substrate round-trips, cross-engine numerical agreement, live knowledge-layer queries, curation gating, and parameter-estimation uncertainty — not just import checks. |
| Versioned releases | ❌ Not done | `pyproject.toml`/`CITATION.cff`/`codemeta.json` all still say `0.0.0` / `0.0.0-phase0`. No git tag exists. |

## What's actually blocking a real "v0.1.0"

1. **The researcher's real name and affiliation** in `CITATION.cff` and `codemeta.json` — I can't fill this in on your behalf; it's factual information only you have. This is the single most concrete, most overdue action item from this whole assessment.
2. **A decision on whether/when this repo goes public** (GitHub) — Zenodo DOI minting requires it, and that's a bigger, more externally-visible step than anything done so far under the "keep everything local" instruction. Worth a deliberate decision, not a default.
3. Once both of those are resolved: bump the version in `pyproject.toml`/`CITATION.cff`/`codemeta.json`, tag it (`git tag v0.1.0`), and — only if you decide to go public — push and connect Zenodo.

Nothing above blocks continued development locally. It blocks *calling* something a
FAIR4RS-compliant release while its own citation metadata still says "TODO."
