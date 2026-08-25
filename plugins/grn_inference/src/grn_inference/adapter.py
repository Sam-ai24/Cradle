from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from cradle.contracts.ai_model_adapter import ModelPrediction


def _conformance_expression() -> dict[str, Any]:
    """A tiny synthetic-but-mechanistic dataset, not an arbitrary
    placeholder: TF1 genuinely drives both targets (in opposite
    directions), TF2 is an uncorrelated decoy, and NoiseGene is driven by
    neither. Same construction `tests/test_grn_inference.py` checks the
    adapter's ground-truth recovery against, so the example a user runs
    from the Explorer exercises the same real case, not a shape-only stub.
    """
    rng = np.random.default_rng(0)
    n_cells = 300
    tf1 = rng.uniform(0, 10, n_cells)
    tf2 = rng.uniform(0, 10, n_cells)
    target1 = 2.0 * tf1 + rng.normal(0, 0.5, n_cells)
    target2 = -1.5 * tf1 + 5 + rng.normal(0, 0.5, n_cells)
    noise_gene = rng.normal(5, 2, n_cells)
    return {
        "expression": {
            "TF1": tf1.tolist(),
            "TF2": tf2.tolist(),
            "Target1": target1.tolist(),
            "Target2": target2.tolist(),
            "NoiseGene": noise_gene.tolist(),
        },
        "candidate_regulators": ["TF1", "TF2"],
    }


class GradientBoostingNetworkInferenceAdapter:
    """Network-inference AI contract (Architecture, Layer 5): expression
    in, a weighted regulator->target graph out.

    Implements the GRNBoost2 algorithm directly (per-target-gene
    gradient-boosted regression against candidate regulators, ranked by
    feature importance) via scikit-learn, rather than depending on the
    `arboreto` reference implementation — confirmed broken against
    current `dask`/`distributed` in testing
    (`TypeError: Must supply at least one delayed object`), not merely
    stale as flagged from research alone. Same algorithm, without the
    broken distributed-computing orchestration layer arboreto wraps it in.
    """

    name = "grnboost2-style"
    contract_type = "network_inference"
    conformance_input = _conformance_expression()

    def predict(self, input: dict[str, Any]) -> ModelPrediction:
        expression: dict[str, list[float]] = input["expression"]
        regulators: list[str] = input["candidate_regulators"]
        n_estimators = input.get("n_estimators", 100)

        gene_names = list(expression.keys())
        regulator_matrix = np.column_stack([expression[name] for name in regulators])

        edges = []
        for target in gene_names:
            if target in regulators:
                continue  # a gene isn't regressed against itself as a candidate regulator
            model = GradientBoostingRegressor(
                n_estimators=n_estimators, max_depth=3, subsample=0.8, learning_rate=0.05, random_state=0
            )
            y = np.asarray(expression[target])
            model.fit(regulator_matrix, y)
            r2 = model.score(regulator_matrix, y)
            for regulator_name, importance in zip(regulators, model.feature_importances_):
                edges.append(
                    {
                        "regulator": regulator_name,
                        "target": target,
                        "importance": float(importance),
                        "r2": float(r2),
                    }
                )

        edges.sort(key=lambda e: e["importance"] * max(e["r2"], 0.0), reverse=True)

        return {
            "output": {"edges": edges},
            "provenance": {
                "model": self.name,
                "contract_type": self.contract_type,
                "method": "gradient_boosted_regression_feature_importance",
                "n_estimators": n_estimators,
                "n_target_genes": len(gene_names) - len(regulators),
                "n_candidate_regulators": len(regulators),
            },
        }
