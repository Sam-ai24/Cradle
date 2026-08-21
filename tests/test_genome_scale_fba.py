from __future__ import annotations

import pytest

pytest.importorskip("cobra")

from cradle.knowledge.cache import cached_download
from cradle.registry import discover

#: iML1515 (Monk et al. 2017, Nature Biotechnology, PMID 29020004) — a
#: real, independently published, highly-cited *E. coli* K-12 MG1655
#: genome-scale metabolic reconstruction (2,712 reactions, 1,877
#: metabolites, 1,516 genes), fetched live from the BiGG Models database.
#: Everything Cradle had validated the COBRApy adapter against before this
#: was a hand-built toy network with an analytically obvious answer
#: (`tests/test_cobrapy_adapter.py`) — this is the adapter's first run
#: against a real, biologically consequential model, unmodified.
_IML1515_URL = "http://bigg.ucsd.edu/static/models/iML1515.xml"

#: Real gene b-numbers, looked up directly from the model itself (not
#: assumed from memory - an earlier guess at accA's b-number was wrong).
_ESSENTIAL_GENES = {"murA": "b3189", "accA": "b0185"}
_NONESSENTIAL_GENES = {"lacZ": "b0344", "lacY": "b0343", "araA": "b0062"}
#: folA (DHFR, b0048) is textbook-essential, but this model's own
#: gene-reaction rule for the DHFR reaction is "b1606 or b0048" - b1606 is
#: folM, a real, independently published secondary dihydrofolate reductase
#: in E. coli (Giladi et al. 2003) the model correctly treats as a
#: redundant isozyme. Knocking out folA alone is therefore genuinely
#: non-lethal in this model, not a false negative - a real nuance this
#: test asserts explicitly rather than picking a cleaner example and
#: hiding it.
_FOLA_GENE_ID = "b0048"


@pytest.fixture(scope="module")
def cobrapy_adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "cobrapy":
            return plugin.instance
    pytest.skip("'cobrapy' simulation adapter is not installed")


@pytest.fixture(scope="module")
def iml1515_path():
    return str(cached_download(_IML1515_URL))


def test_genome_scale_model_predicts_the_known_glucose_minimal_media_growth_rate(
    cobrapy_adapter, iml1515_path
):
    """The real number this session computed by running the unmodified
    genome-scale model through Cradle's existing COBRApy adapter -
    consistent with the widely-cited ~0.87-0.88/h aerobic growth rate for
    E. coli on glucose minimal media (cross-checked against COBRApy's own
    documented example using the related, smaller "textbook" E. coli core
    model under the same condition, which returns a closely matching
    0.874/h - see docs/LANDSCAPE.md for the corroboration this couldn't
    pin down a single literature number for beyond that).
    """
    result = cobrapy_adapter.run({"sbml_path": iml1515_path}, {})

    assert result["status"] == "optimal"
    assert result["objective_value"] == pytest.approx(0.877, abs=0.01)
    assert len(result["trajectories"]) == 2712


def test_essential_gene_knockouts_predict_zero_growth(cobrapy_adapter, iml1515_path):
    """murA (peptidoglycan/cell-wall synthesis) and accA (fatty-acid
    synthesis) have no annotated redundant isozyme in this model and are
    real, independently documented essential genes - the same style of
    validation (in-silico essentiality vs. real experimental essentiality)
    Karr et al. 2012's whole-cell model used for M. genitalium.
    """
    for gene_name, gene_id in _ESSENTIAL_GENES.items():
        result = cobrapy_adapter.run(
            {"sbml_path": iml1515_path}, {"gene_knockouts": [gene_id]}
        )
        assert result["objective_value"] == pytest.approx(0.0, abs=1e-6), (
            f"{gene_name} ({gene_id}) knockout should predict ~zero growth"
        )


def test_nonessential_gene_knockouts_leave_growth_unchanged(cobrapy_adapter, iml1515_path):
    """lacZ/lacY (lactose catabolism) and araA (arabinose catabolism) are
    irrelevant to growth on glucose minimal media - knocking them out
    should not change the predicted growth rate at all.
    """
    baseline = cobrapy_adapter.run({"sbml_path": iml1515_path}, {})["objective_value"]
    for gene_name, gene_id in _NONESSENTIAL_GENES.items():
        result = cobrapy_adapter.run(
            {"sbml_path": iml1515_path}, {"gene_knockouts": [gene_id]}
        )
        assert result["objective_value"] == pytest.approx(baseline, abs=1e-6), (
            f"{gene_name} ({gene_id}) knockout should not affect growth on glucose"
        )


def test_fola_knockout_is_rescued_by_the_models_own_folm_redundancy(
    cobrapy_adapter, iml1515_path
):
    """The interesting negative-ish result, documented rather than swept
    under a cleaner example: folA alone is not lethal in this model,
    because the model's own gene-reaction rule for the DHFR reaction is
    "b1606 or b0048" - b1606 (folM) is a real, published alternative DHFR,
    confirmed by inspecting the model's own GPR annotation directly.
    """
    baseline = cobrapy_adapter.run({"sbml_path": iml1515_path}, {})["objective_value"]
    result = cobrapy_adapter.run(
        {"sbml_path": iml1515_path}, {"gene_knockouts": [_FOLA_GENE_ID]}
    )
    assert result["objective_value"] == pytest.approx(baseline, abs=1e-6)
