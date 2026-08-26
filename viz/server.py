"""Cradle Explorer backend — a real API over the actual plugin registry,
not a fixed demo. Every endpoint here calls the same registered
`DataConnector`/`SimulationAdapter`/`AIModelAdapter` instances the rest
of Cradle uses; nothing here is a separate, parallel implementation.

    powershell -File scripts/run_explorer.ps1

That script watches for *.py changes under viz/, src/, and plugins/ via
`watchfiles`'s own CLI (not `uvicorn --reload`, whose Windows
multiprocessing reloader got stuck mid-restart during development) and
restarts the whole process on change — edit-and-refresh, no manual
restarts.
"""

from __future__ import annotations

import inspect
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import libsbml
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


def _extract_sbml_from_combine_archive(archive_path: str) -> str:
    """A COMBINE archive is a zip file with a manifest.xml listing its
    contents by format URI - find the one COMBINE itself calls out as SBML
    rather than guessing by file extension.
    """
    with zipfile.ZipFile(archive_path) as zf:
        manifest = zf.read("manifest.xml").decode("utf-8")
        root = ET.fromstring(manifest)
        for content in root:
            if "sbml" in content.attrib.get("format", "").lower():
                location = content.attrib["location"].lstrip("./")
                return zf.read(location).decode("utf-8")
    raise ValueError("this COMBINE archive's manifest.xml lists no SBML entry")


def _sbml_text_for_model(model: dict[str, Any]) -> str:
    if "combine_archive" in model:
        return _extract_sbml_from_combine_archive(model["combine_archive"])
    if "sbml_path" in model:
        return Path(model["sbml_path"]).read_text(encoding="utf-8")
    raise ValueError("this model input has neither combine_archive nor sbml_path - can't derive a network from it")


def _species_uniprot_curie(species: Any) -> str | None:
    """The same technique scripts/export_visualization_data.py uses for the
    hand-curated repressilator graph, generalized to any species: read its
    identifiers.org annotation, if it has one pointing at UniProt.

    identifiers.org resolves both a legacy slash form
    (`identifiers.org/uniprot/P03023`, what the repressilator's own model
    uses) and the newer recommended compact-identifier colon form
    (`identifiers.org/uniprot:P03023`, what `cradle.substrate.annotate`
    writes) - a real model found in the wild could use either, so this
    accepts both rather than the one this repo happened to be tested
    against first.
    """
    for i in range(species.getNumCVTerms()):
        cv_term = species.getCVTerm(i)
        for j in range(cv_term.getNumResources()):
            uri = cv_term.getResourceURI(j)
            if "identifiers.org/" not in uri:
                continue
            tail = uri.split("identifiers.org/", 1)[1]
            for prefix in ("uniprot/", "uniprot:"):
                if tail.lower().startswith(prefix):
                    return "uniprot:" + tail[len(prefix) :]
    return None


def _build_network_from_sbml(sbml_text: str, max_species: int = 40, max_reactions: int = 60) -> dict[str, Any]:
    """A bipartite species/reaction graph read directly out of the model's
    own SBML - not a hand-curated abstraction like the repressilator's
    repression ring. Bipartite (species -> reaction -> species) rather
    than collapsing straight to species-species edges because a lot of
    real kinetic reactions are pure synthesis (no reactants) or pure
    degradation (no products); collapsing those to species-species pairs
    would silently drop them from the graph entirely. Large models
    (genome-scale FBA has thousands of species) get an honestly-disclosed
    truncation to the most-connected species, never a silent one.
    """
    document = libsbml.readSBMLFromString(sbml_text)
    model = document.getModel()
    if model is None:
        raise ValueError("libsbml could not parse a model out of this SBML document")

    species_ids = [model.getSpecies(i).getId() for i in range(model.getNumSpecies())]
    reactions = [model.getReaction(i) for i in range(model.getNumReactions())]

    degree: dict[str, int] = {sid: 0 for sid in species_ids}
    reaction_links: list[tuple[str, str, list[str], list[str]]] = []
    for reaction in reactions:
        reactants = [reaction.getReactant(j).getSpecies() for j in range(reaction.getNumReactants())]
        products = [reaction.getProduct(j).getSpecies() for j in range(reaction.getNumProducts())]
        reaction_links.append((reaction.getId(), reaction.getName() or reaction.getId(), reactants, products))
        for species_id in reactants + products:
            degree[species_id] = degree.get(species_id, 0) + 1

    truncated = len(species_ids) > max_species
    kept_species = (
        set(sorted(species_ids, key=lambda sid: degree.get(sid, 0), reverse=True)[:max_species])
        if truncated
        else set(species_ids)
    )

    nodes = []
    for species_id in species_ids:
        if species_id not in kept_species:
            continue
        species = model.getSpecies(species_id)
        nodes.append(
            {
                "data": {
                    "id": species_id,
                    "label": species.getName() or species_id,
                    "curie": _species_uniprot_curie(species),
                    "kind": "species",
                }
            }
        )

    touching = []  # (reaction_id, label, kept_reactants, kept_products)
    for reaction_id, label, reactants, products in reaction_links:
        kept_reactants = [r for r in reactants if r in kept_species]
        kept_products = [p for p in products if p in kept_species]
        if kept_reactants or kept_products:
            touching.append((reaction_id, label, kept_reactants, kept_products))

    # A genome-scale model's few hundred hub metabolites (ATP, water, ...)
    # each touch thousands of reactions - capping species alone still left
    # a genuinely unrenderable/browser-hanging reaction count. Keep the
    # reactions that connect the *most* kept species (more informative
    # than an arbitrary cut), same honest-truncation pattern as species.
    reactions_truncated = len(touching) > max_reactions
    if reactions_truncated:
        touching.sort(key=lambda t: len(t[2]) + len(t[3]), reverse=True)
        touching = touching[:max_reactions]

    edges = []
    for reaction_id, label, kept_reactants, kept_products in touching:
        reaction_node_id = f"rxn:{reaction_id}"
        nodes.append({"data": {"id": reaction_node_id, "label": label, "curie": None, "kind": "reaction"}})
        for reactant_id in kept_reactants:
            edges.append({"data": {"source": reactant_id, "target": reaction_node_id, "label": ""}})
        for product_id in kept_products:
            edges.append({"data": {"source": reaction_node_id, "target": product_id, "label": ""}})

    return {
        "elements": {"nodes": nodes, "edges": edges},
        "n_species_total": len(species_ids),
        "n_reactions_total": len(reactions),
        "n_species_shown": len(kept_species),
        "n_reactions_shown": len(touching),
        "truncated": truncated or reactions_truncated,
    }


class NetworkRequest(BaseModel):
    model: dict[str, Any]


@app.post("/api/network/build")
def network_build(req: NetworkRequest) -> dict[str, Any]:
    """Derive a real Cytoscape-ready graph from any registered model's own
    SBML - the auto-generated counterpart to the repressilator's hand-
    curated regulatory network, usable on whatever's actually loaded rather
    than requiring per-model curation first.
    """
    try:
        sbml_text = _sbml_text_for_model(req.model)
        return _build_network_from_sbml(sbml_text)
    except Exception as exc:  # noqa: BLE001 - surface the real parse/shape error
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/structure/{accession}")
def structure_get(accession: str) -> Response:
    """Proxies a real AlphaFold DB structure through this server (caching
    it under ~/.cradle/cache via the same `cached_download` genome-scale
    models use) so the browser never needs a direct cross-origin fetch to
    alphafold.ebi.ac.uk, which has no CORS headers.
    """
    record = resolve_all(f"uniprot:{accession}").get("alphafold-db")
    pdb_url = (record or {}).get("data", {}).get("pdb_url") if record and "error" not in record else None
    if not pdb_url:
        raise HTTPException(404, f"No AlphaFold DB structure available for uniprot:{accession}")
    local_path = cached_download(pdb_url)
    return Response(content=local_path.read_text(encoding="utf-8"), media_type="text/plain")


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
