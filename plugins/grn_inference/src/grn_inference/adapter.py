from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from cradle.contracts.ai_model_adapter import ModelPrediction


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
