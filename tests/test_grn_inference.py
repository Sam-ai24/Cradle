from __future__ import annotations

import numpy as np
import pytest

from cradle.registry import discover

pytest.importorskip("sklearn")


def _adapter():
    for plugin in discover("ai_model_adapter"):
        if plugin.entry_point_name == "grnboost2-style":
            return plugin.instance
    pytest.skip("'grnboost2-style' network-inference adapter is not installed")


def test_recovers_the_known_driver_and_ignores_the_decoy_regulator():
    """A real ground-truth check, not a shape check: TF1 genuinely drives
    Target1 and Target2; TF2 is a decoy correlated with neither. A correct
    inference should rank TF1's edges to the real targets far above any
    edge involving TF2 or the unrelated NoiseGene, and should not confuse
    noise for signal (NoiseGene's best edge should have a low R²).
    """
    rng = np.random.default_rng(0)
    n_cells = 300
    tf1 = rng.uniform(0, 10, n_cells)
    tf2 = rng.uniform(0, 10, n_cells)  # decoy, drives nothing
    target1 = 2.0 * tf1 + rng.normal(0, 0.5, n_cells)
    target2 = -1.5 * tf1 + 5 + rng.normal(0, 0.5, n_cells)
    noise_gene = rng.normal(5, 2, n_cells)  # driven by neither TF

    expression = {
        "TF1": tf1.tolist(),
        "TF2": tf2.tolist(),
        "Target1": target1.tolist(),
        "Target2": target2.tolist(),
        "NoiseGene": noise_gene.tolist(),
    }

    result = _adapter().predict(
        {"expression": expression, "candidate_regulators": ["TF1", "TF2"]}
    )
    edges = {(e["regulator"], e["target"]): e for e in result["output"]["edges"]}

    assert edges[("TF1", "Target1")]["importance"] > 0.9
    assert edges[("TF1", "Target2")]["importance"] > 0.9
    assert edges[("TF1", "Target1")]["r2"] > 0.9
    assert edges[("TF1", "Target2")]["r2"] > 0.9

    # The decoy TF should not be mistaken for a real regulator of either target.
    assert edges[("TF2", "Target1")]["importance"] < 0.1
    assert edges[("TF2", "Target2")]["importance"] < 0.1

    # Neither TF actually explains the noise gene, whichever gets more
    # "importance" in a coin-flip sense — the fit quality should say so.
    assert edges[("TF1", "NoiseGene")]["r2"] < 0.6
    assert edges[("TF2", "NoiseGene")]["r2"] < 0.6

    # And the ranking overall should put the real edges at the top.
    ranked = result["output"]["edges"]
    top_four = {(e["regulator"], e["target"]) for e in ranked[:4]}
    assert ("TF1", "Target1") in top_four
    assert ("TF1", "Target2") in top_four
