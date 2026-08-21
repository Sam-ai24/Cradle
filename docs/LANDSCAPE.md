# Cradle vs. the field — landscape, comparison, and what "scientific grade" requires

**Written 2026-08-21.** This is a strategic assessment, not a build log — it answers "who
else is doing this, how does Cradle compare, what's left to make it a genuinely useful and
scientific-grade tool." Research on the external landscape used live web search/fetch
rather than relying on memory; citations are given so this can be checked and re-verified
later, since (as Phase 12 found with ESM3/ESM-C's license) things in this space change.

## 1. Who else is building something like this

The field splits into three categories that don't overlap much, and Cradle doesn't sit
cleanly in any one of them — more on why below.

### Legacy mechanistic simulators (no AI, single scale each)

| Tool | Maintainer | Since | Scope | Real-world footprint |
|---|---|---|---|---|
| **VCell** | UConn Health (Loew lab) | 1998 | PDE/stochastic reaction-diffusion, GUI-driven | NIH-funded (R24 GM137787); the closest existing single platform to "general cell modeling," but single-cell-scale, not whole-cell, not AI-integrated |
| **COPASI** | copasi.org consortium | long-running | SBML-based ODE/Gillespie, parameter estimation | Widely used teaching/research tool; Cradle wraps it directly as an adapter |
| **CompuCell3D** | Indiana Univ. (Glazier lab) | Cellular Potts Model since 1992 | Tissue/multicellular | 1,350+ citations on the underlying method; real, continuing adoption in cancer/TB/developmental biology research as of 2026 |
| **PhysiCell** | Macklin lab | 2015 | Agent-based multicellular, 10k-1M cells on a desktop | Won a 2019 PLoS Computational Biology Research Prize for Public Impact |

Cradle already wraps or reproduces the design intent of several of these (COPASI/Tellurium
as adapters; E-Cell4 for the spatial tier CompuCell3D/PhysiCell couldn't fill on Windows).
None of them combine AI model adapters with mechanistic simulation, and none have a
data-connector or license-gating layer — each is a standalone engine at one scale.

### The Karr/Covert whole-cell model lineage — the most directly comparable ambition

- **[Karr et al. 2012, *Cell*](https://www.wholecell.org/models/)** (Stanford, Covert lab):
  the first whole-cell model, of *M. genitalium* — 28 hand-built submodels covering every
  annotated gene product, simulating all 525 possible single-gene knockouts with 79%
  agreement against real experimental essentiality data. This is the closest thing to "a
  virtual cell" that has actually been built and published, and it's the direct
  inspiration/contrast case for Cradle's own architecture.
- **JCVI-syn3A** (*Cell*, Jan 2022; UIUC/JCVI/TU Dresden): a whole-cell kinetic model of a
  493-gene *minimal synthetic* cell — called "the most complete whole-cell computer
  simulation to date" on release, correctly predicting membrane growth and doubling time
  against real experimental data. A 2026 follow-up extended this to a full 4D
  (space + time) spatial-kinetic model of the complete cell cycle.
- **vEcoli** (Covert Lab's *E. coli* whole-cell model, MIT-licensed, actively maintained,
  4,000+ commits): the live edge of this lineage today, built on **Vivarium** (see below).

**The real lesson from this lineage, honestly stated:** each of these is an enormous,
years-long, hand-parameterized effort for *one specific organism*. They prove whole-cell
modeling is *possible*, not that it *generalizes* — the Karr 2012 model was never ported to
a second organism; JCVI-syn3A took a dedicated multi-institution effort for one minimal
synthetic cell. This is exactly the gap Cradle's architecture is a bet against: instead of
one more hand-built monolithic model, build the swappable infrastructure so mechanistic
submodels, AI predictors, and real data can be recombined across organisms and questions
without re-architecting from scratch each time. That bet is unproven at scale (see §3), but
it's a genuinely different strategy than what's been tried, not a redundant one.

### The AI-first "virtual cell" wave — position papers and infrastructure, not delivered systems yet

- **CZI's Virtual Cells Platform.** The field-defining document is
  [Bunne et al. 2024, *Cell*](https://arxiv.org/html/2409.11654v1), "How to Build the
  Virtual Cell with AI" (42 co-authors) — this is a *position paper proposing an aspiration*,
  not a built system. CZI has since funded real infrastructure toward it: a CZI×NVIDIA
  partnership (Oct 2025) funding model/benchmark development at scale, the **Billion Cells
  Project** (Feb 2025, with 10x Genomics/Ultima Genomics) generating a 1B-cell perturbation
  atlas, and **[cz-benchmarks](https://github.com/chanzuckerberg/cz-benchmarks)** — CZI's own
  benchmark tooling, explicitly **alpha/pre-production**, currently scoped only to
  single-cell transcriptomics. CZI's Virtual Cells Platform is a **funding/data/benchmark
  substrate**, not a released simulator — closer in spirit to what Cradle is trying to
  *become* than to a competing product to react to.
- **Arc Institute's State model + Virtual Cell Challenge.** Arc's **State** model has two
  modules (SE: embedding, ST: perturbation-response prediction). Their
  **[Virtual Cell Challenge 2025](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)**
  is a real, large, well-run benchmark — 5,000+ registrants, 114 countries, 1,200+ teams,
  300+ final submissions. **The result, stated plainly by Arc itself: perturbation-
  prediction models are not yet consistently beating naive statistical baselines.** This is
  an important, humbling, and directly relevant data point — it means the entire field's
  best-funded, best-staffed effort at exactly the AI capability Cradle's perturbation
  contract targets hasn't cleared the bar of "better than a naive baseline" yet. Cradle's
  own perturbation contract currently only has empirical (non-ML) baselines — which,
  per this result, is not actually behind the state of the art in any meaningful sense; it's
  in the same place the whole field is.
- **Evo 2** (Arc Institute, Nature 2025/2026): a 40B-parameter genomic language model
  trained on 9.3 trillion nucleotides across 128,000+ species — a sequence/design model, not
  a cell simulator, and the same category Cradle's (unbuilt) sequence contract targets.

### Single-cell foundation models — confirmed predictive/embedding, not mechanistic

| Model | Org | Scale | What it actually is | License |
|---|---|---|---|---|
| Geneformer | Broad | ~104M cells | Masked-gene-prediction embedding model | Apache-2.0 |
| scGPT | bowang-lab | 33M cells | Generative embedding, fine-tunable for perturbation | MIT |
| UCE | Stanford/Snap | Tabula Sapiens-scale | Zero-shot universal cell embedding | MIT, Nature 2026 |
| TranscriptFormer | CZI | 112M cells, 12 species | Generative autoregressive cross-species model | MIT |

All four are statistical pattern-matchers over real single-cell data with **no notion of
molecular mechanism** — this is the load-bearing distinction for Cradle's own design: its
typed AI contracts are meant to sit *alongside* mechanistic simulation (SBML/SED-ML kinetics,
FBA, MD, spatial), not replace it. None of these four projects attempt that combination.

### The nearest actual structural peer: Vivarium

**[Vivarium](https://github.com/vivarium-collective/vivarium-core)** — a composable
process/store/topology engine for multi-scale simulation, and the actual engine underneath
vEcoli above — is the closest real analog to Cradle's plugin-registry idea. But **Vivarium
Core (v1) is no longer under active development** (succeeded by "Vivarium 2.0"/
process-bigraph), and its scope is narrower than Cradle's: simulation-process composition
only, with no data-connector layer, no AI-model contracts, no license-gating mechanism, and
no visualization layer.

## 2. How Cradle actually compares, honestly

**No project found combines all four of Cradle's pieces** — (a) standards-based
kinetic/spatial/MD simulation via swappable engines, (b) typed AI-model contracts sitting
beside mechanistic simulation, (c) CURIE-addressed, license-gated data connectors, and
(d) a Jupyter + browser visualization layer — in one open platform. That's a genuinely
distinctive position, not marketing: the field cleanly splits into legacy single-scale
engines (mechanistic, no AI), foundation models (predictive, no mechanism), and
infrastructure/position papers (aspirational, not yet a working integrated system).

But distinctive scope isn't the same as being ahead. Measured honestly against each
category:

- **vs. legacy engines (VCell/CompuCell3D/PhysiCell/COPASI):** Cradle is far behind on
  scale, adoption, and validation depth — these have 15-30+ years of use, thousands of
  citations, and real research groups depending on them daily. Cradle's validated cases
  (a 2-gene toggle switch, a 3-gene repressilator) are toy-scale by comparison. Cradle's
  advantage isn't capability, it's that it *wraps* several of these rather than competing
  with them — the real question is whether the integration layer adds enough value to
  justify its own complexity, which hasn't been demonstrated on a real research question yet.
- **vs. foundation models (Geneformer/scGPT/UCE/State):** Cradle has exactly one working AI
  adapter (ESM-C protein embeddings) against their many, and zero trained predictive models
  against their several — but per Arc's own Virtual Cell Challenge result, none of them
  are reliably beating naive baselines on perturbation prediction either. This is the one
  place where "behind" is a less clear judgment than it looks: the frontier itself hasn't
  cleared a bar Cradle could meaningfully fail to clear.
- **vs. infrastructure/position efforts (CZI VCP, Arc's Challenge):** these are extremely
  well-funded (CZI, NVIDIA partnership, 10x Genomics data partnerships) multi-year programs
  with dozens of staff; Cradle is a single-session, single-contributor project. The
  comparison here is about ambition and direction more than current capability — Cradle's
  architecture already assumes the thing CZI's benchmark tooling is *becoming* (a
  standardized, swappable evaluation substrate), just built from the mechanistic-simulation
  side rather than the pure-ML side.

**The honest one-line summary:** Cradle is a real, working proof that the swappable-adapter
architecture pattern (data/simulation/AI all behind versioned contracts, with real
conformance testing) can be built cleanly and extended by an outside contributor with zero
help — that's a genuine, verified engineering achievement. It is not yet a demonstrated
*scientific* tool: nothing in it has been peer-reviewed, run at a scale that answers a real
open biological question, or benchmarked against the field's own evaluation efforts.

## 3. What "scientific grade" actually requires from here

In roughly the order that would matter most:

1. **A real predictive AI result, honestly benchmarked.** ~~Complete at least one of the
   deferred embedding/perturbation/structure contracts against real trained weights~~ —
   **embedding half done, 2026-08-21**: `esmc_embedding` (protein sequences) and
   `geneformer_embedding` (single-cell expression) are both real now. Still fully open:
   the perturbation contract (what the Virtual Cell Challenge/VCBench actually evaluate,
   as opposed to embedding), and — for either contract — an actual public benchmark
   submission. Losing to the naive baseline and *publishing that honestly* — as Arc itself
   did — is still a legitimate scientific-grade outcome; silence is not.
2. **Scale demonstration.** ~~Run the FBA adapter on a real genome-scale model~~ — **done,
   2026-08-21**: the unmodified COBRApy adapter now runs iML1515 (2,712 reactions, 1,516
   genes), correctly predicting the real published growth rate and correctly classifying
   real essential/non-essential gene knockouts (see `docs/ROADMAP.md`'s Phase 2 addendum).
   Still open: infer a GRN from a real single-cell dataset instead of an 8-cell synthetic
   one; run MD on a real small-molecule/peptide system instead of a bead-spring toy chain.
3. **Independent peer review.** A methods paper (architecture + validation results) submitted
   somewhere real — even a workshop paper or a bioRxiv preprint — moves this from "internally
   validated" to "externally checked." This is the single biggest lever for "scientific
   grade" as a label, separate from any specific new capability.
4. **A real external user.** Phase 11's own exit criterion (a lab collaborator runs a
   workflow from a notebook without reading source code) has been simulated by a fresh
   agent, not tested with an actual biologist. That's the qualitative signal that would
   matter most and hasn't happened yet.
5. **Public release + citable versioning.** Currently local-only per your own instruction —
   at some point that has to change for anyone outside this conversation to use, cite, or
   build on it. Phase 6 already flagged this as blocked on your decision (real name for
   `CITATION.cff`, and whether/when this goes public); nothing else in the roadmap can
   substitute for actually publishing it.
6. **GPU/HPC-scale execution, tested for real.** ESM-C ran CPU-only in this session; OpenMM's
   GPU path, and anything at real single-cell-atlas scale, needs actual GPU hardware to prove
   out, not just code that should theoretically work on one.

## 4. What would make it a better *product* (beyond "scientific grade")

These are more about usefulness/adoption than pure scientific rigor:

- **A model zoo/catalog** beyond the two current curated examples — a handful of real,
  independently-curated models (metabolic, signaling, regulatory) that researchers could
  actually reuse, the same way BioModels itself works but pre-integrated with Cradle's
  provenance/curation tooling.
- **Richer visualization**, generalized beyond the repressilator-specific Phase 10 demo —
  a researcher should be able to point the scale-router at *their own* model, not just the
  one built-in example.
- **A hosted/deployed instance** (even a simple one) so people can try it without a local
  Python environment setup — currently every capability requires cloning the repo and
  managing a venv.
- **Tutorials and an example gallery** aimed at biologists, not just the architecture
  documentation aimed at contributors — `CONTRIBUTING.md` and `docs/ARCHITECTURE.md` are
  good engineering docs, not onboarding for a wet-lab researcher.
- **ELN/LIMS integration beyond a Markdown export** — real lab-notebook software
  (Benchling, LabArchives, etc.) integration would make the "lab-facing" framing in Phase 11
  actually land in a real workflow, not just produce a file that could theoretically go in one.
- **A second, independently-curated organism/model system** — proving the architecture
  generalizes beyond the repressilator/toggle-switch pair is worth more for credibility than
  almost any other single addition, since it directly answers "does this actually generalize"
  rather than "does this work for the one case we tried."

## 5. Where this is realistically headed

Given the pace and pattern so far (13 roadmap phases touched in two days, each with real,
checked, honestly-reported findings), the highest-leverage next moves are:

1. Finish at least one real trained AI model behind an existing typed contract — **the
   embedding half is done, 2026-08-21**: `esmc_embedding` (protein sequences) and
   `geneformer_embedding` (single-cell expression, the model this comparison's own table
   always named as the intended default) are both real, working, license-clean
   implementations now. Still open: an actual public benchmark submission (VCBench /
   Arc's Virtual Cell Challenge) — neither adapter has been scored against one yet, and
   perturbation prediction (not embedding) is what those benchmarks actually evaluate, so
   this doesn't yet close the "honestly benchmarked" half of this recommendation.
2. ~~Run one existing capability at real scale~~ — **done, 2026-08-21**: genome-scale FBA
   against iML1515, see above. The same "run it unmodified at real scale" move is still
   open for the GRN-inference and MD adapters.
3. Make the public-release decision (Phase 6's blocker) — everything past this point matters
   more once outside people can actually see and use it.
4. Find one real external user or collaborator for an actual question, even a small one.

None of this requires new architecture — the swappable-adapter pattern is proven; what's
missing now is scale, a real predictive result, and outside eyes.
