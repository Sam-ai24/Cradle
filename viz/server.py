"""Cradle Explorer backend — a real API over the actual plugin registry,
not a fixed demo. Every endpoint here calls the same registered
`DataConnector`/`SimulationAdapter`/`AIModelAdapter` instances the rest
of Cradle uses; nothing here is a separate, parallel implementation.

    uvicorn server:app --reload --app-dir viz --port 8743

`--reload` watches this file (and its imports under `src/`) and restarts
the server automatically on save — edit-and-refresh, no manual restarts.
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cradle.conformance import fixtures as cf
from cradle.contracts.errors import NotConfiguredError
from cradle.knowledge.cache import cached_download
from cradle.knowledge.router import resolve_all
from cradle.registry import GROUPS, discover

REPO_ROOT = Path(__file__).resolve().parent.parent
IML1515_URL = "http://bigg.ucsd.edu/static/models/iML1515.xml"
_EXAMPLE_DIR = Path(tempfile.mkdtemp(prefix="cradle_explorer_"))

app = FastAPI(title="Cradle Explorer")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# `discover(kind)` reconstructs every plugin of that kind on every call -
# fine for the CLI conformance runner (once per process), too slow for an
# interactive API where several heavy ML adapters (esmc/geneformer/gears)
# would otherwise get rebuilt on every single request. Cache the
# discovered instances for this process's lifetime instead; `--reload`
# already gives a fresh process (and fresh cache) on every code change.
_PLUGIN_CACHE: dict[str, list] = {}


def _plugins(kind: str) -> list:
    if kind not in _PLUGIN_CACHE:
        _PLUGIN_CACHE[kind] = discover(kind)
    return _PLUGIN_CACHE[kind]


def _find(kind: str, name: str) -> Any:
    for plugin in _plugins(kind):
        if plugin.entry_point_name == name:
            return plugin.instance
    raise HTTPException(404, f"no {kind} named '{name}' is registered")


def _short_description(instance: Any) -> str | None:
    """First real sentence of the adapter class's own docstring - the same
    text a developer reading the source would see, not a separate summary
    that could drift out of sync with it.
    """
    doc = inspect.getdoc(type(instance))
    if not doc:
        return None
    first_para = doc.split("\n\n", 1)[0].replace("\n", " ").strip()
    return first_para[:220]


@app.get("/api/plugins")
def list_plugins() -> dict[str, list[dict[str, Any]]]:
    """Every registered plugin, by kind — the actual, live inventory,
    not a hardcoded list. If a plugin isn't pip-installed in this venv,
    it genuinely won't appear here, same as `cradle-conformance`.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for kind in GROUPS:
        plugins = _plugins(kind)
        out[kind] = [
            {
                "name": p.entry_point_name,
                "distribution": p.distribution,
                "contract_type": getattr(p.instance, "contract_type", None),
                "input_mode": getattr(p.instance, "input_mode", None),
                "description": _short_description(p.instance),
            }
            for p in plugins
        ]
    return out


@app.get("/api/data/resolve")
def data_resolve(curie: str) -> dict[str, Any]:
    """Fan one CURIE out across every registered data connector that
    can answer it — the exact same `cradle.knowledge.router.resolve_all`
    every other part of Cradle uses.
    """
    return resolve_all(curie)


@app.get("/api/ai/example/{name}")
def ai_example(name: str) -> dict[str, Any]:
    instance = _find("ai_model_adapter", name)
    return getattr(instance, "conformance_input", {"probe": True})


class PredictRequest(BaseModel):
    input: dict[str, Any]


@app.post("/api/ai/predict/{name}")
def ai_predict(name: str, req: PredictRequest) -> dict[str, Any]:
    instance = _find("ai_model_adapter", name)
    try:
        return instance.predict(req.input)
    except NotConfiguredError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface the adapter's own real error message
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/sim/example/{name}")
def sim_example(name: str) -> dict[str, Any]:
    """A real, runnable example input for `name`, built from the exact
    same fixtures `cradle.conformance.checks` uses to test this adapter
    - never a hand-invented shape that could be wrong.
    """
    instance = _find("simulation_adapter", name)
    input_mode = getattr(instance, "input_mode", "toy_dict")

    if input_mode == "combine_archive":
        archive_path = str(REPO_ROOT / "models" / "repressilator" / "repressilator.omex")
        return {"model": {"combine_archive": archive_path}, "config": {}}
    if input_mode == "fba_sbml":
        try:
            iml1515_path = str(cached_download(IML1515_URL))
        except Exception:  # noqa: BLE001 - offline fallback to the tiny toy network
            iml1515_path = cf.build_reference_fba_sbml(str(_EXAMPLE_DIR))
        return {"model": {"sbml_path": iml1515_path}, "config": {}}
    if input_mode == "md_manifest":
        return {"model": {"manifest_path": cf.build_reference_md_manifest(str(_EXAMPLE_DIR))}, "config": {}}
    if input_mode == "spatial_manifest":
        return {"model": {"manifest_path": cf.build_reference_spatial_manifest(str(_EXAMPLE_DIR))}, "config": {}}
    if input_mode == "qual_sbml":
        from cradle.substrate.examples.boolean_toggle import write_sbml

        sbml_path = write_sbml(str(_EXAMPLE_DIR / "boolean_toggle.xml"))
        return {"model": {"sbml_path": sbml_path}, "config": {"n_steps": 4}}
    return {"model": {"k": 0.5, "x0": 10.0}, "config": {"t_end": 1.0, "steps": 5}}


class SimulateRequest(BaseModel):
    model: dict[str, Any]
    config: dict[str, Any] = {}


@app.post("/api/sim/run/{name}")
def sim_run(name: str, req: SimulateRequest) -> dict[str, Any]:
    instance = _find("simulation_adapter", name)
    try:
        return instance.run(req.model, req.config)
    except NotConfiguredError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


class NoCacheStaticFiles(StaticFiles):
    """Plain `StaticFiles` lets the browser cache HTML/CSS/JS aggressively
    with no revalidation, which silently served stale `explorer.css` and
    `app.js` after edits during this same session (confirmed live: a
    function's own source, read back via `.toString()`, was still the
    pre-edit version after a manual reload) - exactly the "can't see what
    you're editing" failure hot-reload was supposed to prevent. These files
    are actively edited during development, not versioned production
    assets, so never cache them.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


# Static frontend last, so /api/* above always wins over the catch-all.
app.mount("/", NoCacheStaticFiles(directory=str(Path(__file__).parent), html=True), name="static")
