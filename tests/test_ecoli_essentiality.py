"""E. coli essentiality flagship: comparison math is tested against
hand-checked fixtures; live iML1515/UniProt/STRING are tested only for
the published artifact and a few known genes, not by re-solving 1,516
LPs in every pytest run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cradle.lab.essentiality import (
    KNOWN,
    auroc,
    binary_metrics,
    classify_fba_growth,
    compare_essentiality,
    confusion_counts,
)

FLAGSHIP_RESULTS = (
    Path(__file__).resolve().parent.parent / "models" / "ecoli_flagship" / "results.json"
)


def test_classify_fba_growth_uses_one_percent_of_wild_type():
    assert classify_fba_growth(0.0, 0.877) == "essential"
    assert classify_fba_growth(0.008, 0.877) == "essential"
    assert classify_fba_growth(0.877, 0.877) == "nonessential"
    assert classify_fba_growth(None, 0.877) == "essential"


def test_confusion_and_metrics_on_a_hand_checked_table():
    # 2 TP, 1 FP, 3 TN, 1 FN
    pairs = [
        (True, True),
        (True, True),
        (True, False),
        (False, False),
        (False, False),
        (False, False),
        (False, True),
    ]
    counts = confusion_counts(pairs)
    assert counts == {"tp": 2, "fp": 1, "tn": 3, "fn": 1}
    metrics = binary_metrics(counts)
    assert metrics["n"] == 7
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["accuracy"] == pytest.approx(5 / 7)


def test_auroc_perfect_and_randomish():
    assert auroc([3.0, 2.0, 1.0], [True, True, False]) == pytest.approx(1.0)
    assert auroc([1.0, 1.0], [True, False]) == pytest.approx(0.5)
    assert auroc([1.0], [True]) is None


def test_compare_essentiality_joins_three_layers_on_bnumbers():
    deletion = {
        "baseline_growth": 1.0,
        "genes": {
            "b3189": {"growth": 0.0, "status": "optimal"},
            "b0344": {"growth": 1.0, "status": "optimal"},
            "b0048": {"growth": 1.0, "status": "optimal"},
        },
    }
    gene_table = {
        "genes": [
            {"id": "b3189", "name": "murA", "annotation": {"uniprot": ["P0A749"]}},
            {"id": "b0344", "name": "lacZ", "annotation": {"uniprot": ["P00722"]}},
            {"id": "b0048", "name": "folA", "annotation": {"uniprot": ["P0ABQ4"]}},
        ]
    }
    literature = {
        "labels": {
            "b3189": {"literature_essential": True, "uniprot": "P0A749", "curie": "uniprot:P0A749", "gene_primary": "murA"},
            "b0344": {"literature_essential": False, "uniprot": "P00722", "curie": "uniprot:P00722", "gene_primary": "lacZ"},
            "b0048": {"literature_essential": True, "uniprot": "P0ABQ4", "curie": "uniprot:P0ABQ4", "gene_primary": "folA"},
        }
    }
    string_degrees = {
        "by_bnumber": {
            "b3189": {"string_id": "511145.b3189", "preferred_name": "murA", "degree": 40},
            "b0344": {"string_id": "511145.b0344", "preferred_name": "lacZ", "degree": 2},
            "b0048": {"string_id": "511145.b0048", "preferred_name": "folA", "degree": 15},
        },
        "name_to_id": {},
        "degree_by_id": {},
    }
    comparison = compare_essentiality(deletion, gene_table, literature, string_degrees)
    by_id = {row["gene_id"]: row for row in comparison["rows"]}
    assert by_id["b3189"]["fba_essential"] is True
    assert by_id["b0344"]["fba_essential"] is False
    assert by_id["b0048"]["fba_essential"] is False
    assert comparison["fba_vs_literature"]["counts"]["tp"] == 1
    assert comparison["fba_vs_literature"]["counts"]["fn"] == 1  # folA
    assert comparison["fba_vs_literature"]["counts"]["tn"] == 1
    lit_only = comparison["disagreements"]["literature_essential_fba_not"]
    assert [row["gene_id"] for row in lit_only] == ["b0048"]
    assert comparison["string_vs_literature"]["auroc"] == pytest.approx(1.0)


@pytest.mark.skipif(not FLAGSHIP_RESULTS.exists(), reason="flagship results.json not published yet")
def test_published_flagship_keeps_the_known_gene_nuances():
    import json

    payload = json.loads(FLAGSHIP_RESULTS.read_text())
    comparison = payload["comparison"]
    observed = {item["name"]: item for item in comparison["known_genes"]}

    murA = observed["murA"]["observed"]
    lacZ = observed["lacZ"]["observed"]
    folA = observed["folA"]["observed"]
    assert murA["gene_id"] == KNOWN["murA"]["id"]
    assert murA["fba_essential"] is True
    assert murA["literature_essential"] is True
    assert lacZ["fba_essential"] is False
    assert lacZ["literature_essential"] is False
    # The documented isozyme rescue — literature essential, FBA not.
    assert folA["fba_essential"] is False
    assert folA["literature_essential"] is True
    assert comparison["baseline_growth"] == pytest.approx(0.877, abs=0.01)
    assert comparison["n_model_genes"] == 1516
    # FBA has to be at least as correlated as chance with PEC labels.
    assert comparison["fba_vs_literature"]["metrics"]["mcc"] > 0.0
