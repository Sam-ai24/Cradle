# Contributing a plugin to Cradle

This is the complete guide for adding a new data connector, simulation adapter, or AI
model adapter to Cradle **without needing help from the core team** — that's a deliberate
design goal (Roadmap Phase 12's exit criterion), not just an aspiration. If you get stuck,
that's a bug in this document or in `cradle.contracts`/`cradle.conformance` — please open an
issue describing exactly where the trail went cold.

Read `docs/ARCHITECTURE.md` first for *why* Cradle is built this way (standards define the
swap boundaries, not Cradle's own code). This document is the *how*.

## The three plugin kinds

Every plugin is one of three kinds, each with its own typed `Protocol` in
`src/cradle/contracts/`:

| Kind | Protocol | Registers under entry_points group |
|---|---|---|
| Data connector | `cradle.contracts.data_connector.DataConnector` | `cradle.data_connectors` |
| Simulation adapter | `cradle.contracts.simulation_adapter.SimulationAdapter` | `cradle.simulation_adapters` |
| AI model adapter | `cradle.contracts.ai_model_adapter.AIModelAdapter` | `cradle.ai_model_adapters` |

Cradle's core (`src/cradle/`) never imports a specific plugin. It discovers plugins at
runtime via Python's standard `importlib.metadata.entry_points` mechanism
(`src/cradle/registry.py`) — the same mechanism pytest itself uses for its own plugins. This
means **adding a plugin never requires changing Cradle's own code**, only publishing a new,
independently-installable Python package that declares an entry point.

## Step 1 — scaffold a new package

A plugin is an ordinary, independently-installable Python package (its own `pyproject.toml`,
its own `src/<your_package>/` layout) with one dependency on `cradle-core` and one
`[project.entry-points."cradle.<kind>s"]` table. The three simplest possible real examples,
each under 30 lines, are the reference plugins in `plugins/`:

- `plugins/hello_data/` — the minimal `DataConnector`
- `plugins/hello_sim/` — the minimal `SimulationAdapter`
- `plugins/hello_ai/` — the minimal `AIModelAdapter`

Copy whichever is closest to what you're building as your starting `pyproject.toml` shape.
The entry-points table is the part that matters:

```toml
[project.entry-points."cradle.simulation_adapters"]
your-engine-name = "your_package.adapter:build_adapter"
```

The right-hand side is `module:attribute`. The attribute can be a class (called with no
arguments to construct an instance) or a zero-argument factory function — see
`plugins/llm_orchestrator/` for the factory-function style (used there because the same
class is instantiated twice, once per provider) versus `plugins/hello_sim/`'s direct-class
style.

## Step 2 — implement the contract

Each `Protocol` is intentionally small. Implement exactly its methods/attributes — nothing
else is required, and conformance doesn't care about anything beyond the contract.

### DataConnector

```python
class YourConnector:
    name = "your-source"
    # Optional: a real CURIE your connector can actually answer, used as the
    # conformance smoke-test probe instead of the Phase 0 placeholder "test:0000".
    conformance_curie = "uniprot:P04637"

    def fetch(self, curie: str) -> ConnectorRecord:
        ...  # must return {"curie", "source", "license", "data"} — see below
```

**CURIE format.** Every `curie` argument is `namespace:local_id` (identifiers.org/MIRIAM
convention — see `docs/ARCHITECTURE.md` Layer 6), e.g. `uniprot:P04637`. This isn't
mechanically enforced by the `DataConnector` Protocol itself (it's typed as a plain `str`),
so parse and validate it yourself — reject anything with the wrong namespace or a malformed
local id, rather than assuming `fetch()` is only ever called with input meant for you. Check
identifiers.org for whether your source already has a registered namespace prefix before
inventing one.

**What conformance actually checks.** `check_data_connector` (in
`cradle/conformance/checks.py`) calls `fetch(conformance_curie)` and asserts the returned
dict has all four `ConnectorRecord` keys present (`curie`, `source`, `license`, `data`) —
it does not check that `data` is non-empty or that the call was live rather than cached, so
passing conformance is a floor, not a substitute for the real correctness test in Step 4.

**Error handling.** Nothing in the contract mandates a specific exception type for a bad or
non-existent id — raise whatever's clearest (`ValueError` is a reasonable default) with a
message naming the actual input that failed, rather than returning a record full of `None`s.
Watch for APIs that don't cleanly signal "not found" via HTTP status — some return 200 with
an empty/partial payload for an id that's syntactically valid but never assigned; check for
that directly against the live API rather than assuming a 4xx/2xx split is enough.

**Live HTTP calls.** Prefer `cradle.knowledge.http.get_json`/`get_text` over calling
`requests` directly — they already retry transient failures (timeouts, connection errors,
5xx) with backoff and raise immediately on a 4xx, a real fix from Phase 6 after a live
timeout flaked an otherwise-correct connector mid-run. `HttpError` is what they raise on an
unretryable failure.

`ConnectorRecord` (`cradle.contracts.data_connector.ConnectorRecord`) requires all four
keys: `curie` (echo the input), `source` (a human-readable name for where this came from),
`license` (the source's actual license — not a placeholder), and `data` (a dict of whatever
your source returns). Every record must be traceable to a real license — this is
Architecture Layer 8's "no unsourced numbers" rule, enforced by convention here since it
can't be mechanically checked from the record shape alone.

If your source has redistribution/commercial-use restrictions (see `NOTICE.md` for examples
already handled this way — KEGG, DepMap), wrap your connector in
`cradle.knowledge.gate.LicenseGate` rather than baking the restriction into your own class:

```python
def build_connector():
    return LicenseGate(YourRawConnector(), license_summary="non-commercial only, see ...")
```

`LicenseGate` is off by default; a deployment turns it on by calling `.acknowledge()` or
setting `CRADLE_LICENSE_ACK_<NAME>=1`. `cradle.conformance.checks.check_data_connector`
specifically verifies a gated connector *refuses* until acknowledged, then verifies it
*works* once acknowledged — both paths are checked, not just documented.

### SimulationAdapter

```python
class YourAdapter:
    name = "your-engine"
    input_mode = "combine_archive"  # or "toy_dict" (default), "fba_sbml", "md_manifest",
                                     # "qual_sbml", "spatial_manifest" — pick whichever
                                     # matches what your engine actually consumes

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        ...  # must return {"t", "trajectories", "engine"}
```

`input_mode` determines which conformance fixture `cradle.conformance.checks` runs your
adapter against (see `check_simulation_adapter`'s dispatch table). If your engine consumes
something genuinely new — no existing `input_mode` fits — that's a real, welcome extension
point: add a new `input_mode` string, a new `_check_..._simulation_adapter` function in
`cradle/conformance/checks.py`, and a new fixture builder in
`cradle/conformance/fixtures.py`, following the pattern of `md_manifest`/`qual_sbml`/
`spatial_manifest` (each added in a phase that needed a genuinely new execution tier, per
`docs/ARCHITECTURE.md`). This is additive — existing `input_mode`s keep working unchanged.

If your engine is GPL/AGPL-licensed, run it subprocess- or container-isolated (never import
it directly into your adapter's process) — see `plugins/cobrapy_fba/`'s `worker.py` +
`python -m` pattern, and add your dependency to the isolation table in `NOTICE.md`.

### AIModelAdapter

```python
class YourAdapter:
    name = "your-model"
    contract_type = "embedding"  # or "perturbation", "sequence", "structure",
                                  # "orchestration", "network_inference"
    # Optional: a real, small probe input conformance should actually run
    # (skip this only if {"probe": True} or the built-in per-contract-type
    # default in checks.py genuinely fits your model).
    conformance_input = {"sequence": "MQIFVKTLTGKTITLEVEPSDT..."}

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        ...  # must return {"output", "provenance"}
```

If your model needs an API key, a license acknowledgment, or gated weights, raise
`cradle.contracts.errors.NotConfiguredError` (with a message naming exactly what's missing
and how to get it) rather than crashing or silently returning a placeholder. The conformance
runner treats this as a **skip**, not a failure — see `plugins/llm_orchestrator/` (missing
API key) and `plugins/biogrid_data/` (missing registered key) for two real examples of this
exact pattern. Check whether your model's weights are *actually* license-restricted before
assuming they need this — `plugins/esmc_embedding/` was built in Phase 12 after directly
checking (via the HuggingFace API's `gated` field and the model's own `LICENSE.md`) that its
specific checkpoint carries no such restriction, correcting an earlier assumption in
`docs/ARCHITECTURE.md`/`NOTICE.md` that it did. Verify, don't assume.

## Step 3 — install and verify

```bash
pip install -e plugins/your_plugin_name
python -c "from cradle.registry import discover; print([p.entry_point_name for p in discover('simulation_adapter')])"
cradle-conformance   # discovers + verifies every registered plugin, including yours
```

`cradle-conformance` (`src/cradle/conformance/cli.py`) prints `PASS`/`FAIL`/`SKIP` per
plugin and exits non-zero if anything failed (a `SKIP` — `NotConfiguredError` — is not a
failure). This is the actual mechanical proof your plugin satisfies its contract; nothing
about registering a plugin requires anyone to read or approve your implementation first.

## Step 4 — write a real correctness test, not a shape check

Every plugin already in this repo is tested against a real, checkable fact about its
domain — a known ground-truth value, a physical law, an analytically obvious optimum — not
just "did it return the right dict keys." A few examples to calibrate against:
`tests/test_ecell4_spatial_adapter.py` (particle spread must match `sqrt(2Dt)`),
`tests/test_grn_inference.py` (a synthetic driver gene must rank above a synthetic decoy),
`tests/test_esmc_embedding.py` (two unrelated real proteins must produce different
embeddings, not just correctly-shaped ones). Aim for the same bar.

## Semver policy

Every plugin package is its own independently-versioned distribution (each has its own
`pyproject.toml` with its own `version`). Follow standard semver relative to your plugin's
own public surface (the contract methods you implement, plus anything else you export):

- **Patch** (`0.0.x`): bug fixes that don't change behavior a caller could have relied on.
- **Minor** (`0.x.0`): new capability that's additive — a new optional input field, a new
  `conformance_curie`/`conformance_input`, a new `input_mode` your adapter now also accepts.
- **Major** (`x.0.0`): anything that changes what an existing valid call returns, or removes
  something.

Cradle's own shared contracts (`cradle.contracts.*`) are versioned the same way and are
meant to only grow additively across phases — see how the perturbation contract added a
`kind` field in Phase 8 (`cradle.perturbation`) without breaking Phase 5's original shape,
proven by a dedicated test showing the old shape still validates. If your plugin needs a
contract change that *isn't* additive, that's a Cradle-core discussion (open an issue), not
something to work around in your own package.

## What review actually checks

Since a plugin registers without any Cradle-core code change, "review" here means: does
`cradle-conformance` pass, does the plugin have a real correctness test (not just a shape
check), does any GPL/restricted-license dependency follow the isolation/gating patterns
above, and does `NOTICE.md` get updated if you added a new third-party license
consideration. There is no separate approval gate beyond that.
