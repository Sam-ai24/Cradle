from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "viz"))

pytest.importorskip("libsbml")
pytest.importorskip("fastapi")

from cradle.conformance.fixtures import build_reference_combine_archive, build_reference_fba_sbml  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server as explorer_server  # noqa: E402

#: build_reference_combine_archive's toggle-switch model (Phase 1) reuses
#: the exact two real proteins the repressilator's export script also
#: annotates against - LacI (present in AlphaFold DB) and bacteriophage
#: lambda's CI repressor (confirmed genuinely absent from AlphaFold DB,
#: not a transient failure - see scripts/export_visualization_data.py's
#: own comment). Using a *different* model than the repressilator here
#: proves the network-building code generalizes rather than being
#: implicitly tuned to one archive.
_LACI_ACCESSION = "P03023"
_LAMBDA_CI_ACCESSION = "P03034"


@pytest.fixture(scope="module")
def client():
    return TestClient(explorer_server.app)


def test_list_plugins_reports_every_registered_group(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == set(explorer_server.GROUPS)
    for plugins in body.values():
        for plugin in plugins:
            assert plugin["name"]
            assert "description" in plugin  # may be None, but the key must exist


def test_extract_sbml_from_combine_archive_returns_the_real_sbml_text(tmp_path):
    archive_path = build_reference_combine_archive(str(tmp_path))
    sbml_text = explorer_server._extract_sbml_from_combine_archive(archive_path)
    assert "<sbml" in sbml_text
    assert _LACI_ACCESSION in sbml_text


def test_extract_sbml_rejects_an_archive_with_no_sbml_entry(tmp_path):
    import zipfile

    archive_path = tmp_path / "empty.omex"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr(
            "manifest.xml",
            '<?xml version="1.0"?><omexManifest xmlns="http://identifiers.org/combine.specifications/omex-manifest">'
            '<content location="notes.txt" format="text/plain" master="true"/></omexManifest>',
        )
        zf.writestr("notes.txt", "no model here")

    with pytest.raises(ValueError, match="no SBML entry"):
        explorer_server._extract_sbml_from_combine_archive(str(archive_path))


def test_sbml_text_for_model_reads_a_plain_sbml_path_too(tmp_path):
    sbml_path = build_reference_fba_sbml(str(tmp_path))
    text = explorer_server._sbml_text_for_model({"sbml_path": sbml_path})
    assert "<sbml" in text


def test_sbml_text_for_model_rejects_a_model_with_no_sbml_source():
    with pytest.raises(ValueError, match="combine_archive.*sbml_path"):
        explorer_server._sbml_text_for_model({"k": 0.5, "x0": 10.0})


def test_build_network_reflects_the_models_own_real_species_and_annotations(tmp_path):
    """Not a shape-only check: the toggle-switch model's own SBML names its
    two species U and V and annotates them against real UniProt entries -
    this must come from that annotation, not be guessed or hardcoded here.
    """
    archive_path = build_reference_combine_archive(str(tmp_path))
    sbml_text = explorer_server._extract_sbml_from_combine_archive(archive_path)
    graph = explorer_server._build_network_from_sbml(sbml_text)

    species_nodes = {n["data"]["id"]: n["data"] for n in graph["elements"]["nodes"] if n["data"]["kind"] == "species"}
    assert set(species_nodes) == {"U", "V"}
    assert species_nodes["U"]["curie"] == f"uniprot:{_LACI_ACCESSION}"
    assert species_nodes["V"]["curie"] == f"uniprot:{_LAMBDA_CI_ACCESSION}"

    reaction_nodes = [n for n in graph["elements"]["nodes"] if n["data"]["kind"] == "reaction"]
    assert reaction_nodes, "a toggle switch has real production/degradation reactions to show"

    assert graph["n_species_total"] == 2
    assert graph["truncated"] is False


def test_build_network_edges_only_connect_nodes_that_are_actually_present(tmp_path):
    archive_path = build_reference_combine_archive(str(tmp_path))
    sbml_text = explorer_server._extract_sbml_from_combine_archive(archive_path)
    graph = explorer_server._build_network_from_sbml(sbml_text)

    node_ids = {n["data"]["id"] for n in graph["elements"]["nodes"]}
    for edge in graph["elements"]["edges"]:
        assert edge["data"]["source"] in node_ids
        assert edge["data"]["target"] in node_ids


def test_build_network_truncates_honestly_when_capped_below_the_real_species_count(tmp_path):
    archive_path = build_reference_combine_archive(str(tmp_path))
    sbml_text = explorer_server._extract_sbml_from_combine_archive(archive_path)

    graph = explorer_server._build_network_from_sbml(sbml_text, max_species=1)

    assert graph["truncated"] is True
    assert graph["n_species_shown"] == 1
    assert graph["n_species_total"] == 2  # the real total is still reported, not silently hidden


def test_build_network_caps_reaction_count_independently_of_species_count():
    """A regression test for a real bug hit live this session: capping
    species alone still let a hub species (touching many reactions) pull
    in an unrenderable number of reaction nodes - building this against
    the real genome-scale iML1515 model hung a browser tab. Reproduced
    here with a small synthetic SBML instead of the ~11MB real download.
    """
    species_block = "".join(
        f'<species id="S{i}" name="S{i}" compartment="c" initialAmount="1"/>' for i in range(3)
    )
    # One hub species (S0) participates as a reactant in every reaction;
    # each reaction also produces a unique product so there are more
    # reactions than the cap allows.
    reactions_block = "".join(
        f'<reaction id="R{i}"><listOfReactants><speciesReference species="S0"/></listOfReactants>'
        f'<listOfProducts><speciesReference species="S1"/></listOfProducts></reaction>'
        for i in range(10)
    )
    sbml_text = (
        '<?xml version="1.0"?>'
        '<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" level="3" version="1">'
        '<model id="synthetic_hub_model">'
        f'<listOfCompartments><compartment id="c" size="1"/></listOfCompartments>'
        f"<listOfSpecies>{species_block}</listOfSpecies>"
        f"<listOfReactions>{reactions_block}</listOfReactions>"
        "</model></sbml>"
    )

    graph = explorer_server._build_network_from_sbml(sbml_text, max_species=10, max_reactions=3)

    reaction_nodes = [n for n in graph["elements"]["nodes"] if n["data"]["kind"] == "reaction"]
    assert len(reaction_nodes) == 3
    assert graph["n_reactions_shown"] == 3
    assert graph["n_reactions_total"] == 10
    assert graph["truncated"] is True


def test_build_network_endpoint_round_trips_through_http(client, tmp_path):
    archive_path = build_reference_combine_archive(str(tmp_path))
    response = client.post("/api/network/build", json={"model": {"combine_archive": archive_path}})
    assert response.status_code == 200
    body = response.json()
    assert body["n_species_total"] == 2


def test_build_network_endpoint_reports_a_bad_model_as_400_not_500(client):
    response = client.post("/api/network/build", json={"model": {"k": 0.5}})
    assert response.status_code == 400
    assert "combine_archive" in response.json()["detail"]


def test_structure_endpoint_proxies_a_real_present_alphafold_structure(client):
    response = client.get(f"/api/structure/{_LACI_ACCESSION}")
    assert response.status_code == 200
    assert "ATOM" in response.text


def test_structure_endpoint_reports_a_genuinely_missing_structure_as_404_not_500(client):
    response = client.get(f"/api/structure/{_LAMBDA_CI_ACCESSION}")
    assert response.status_code == 404
