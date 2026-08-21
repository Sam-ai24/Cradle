from __future__ import annotations

import pytest

geneformer_embedding = pytest.importorskip("geneformer_embedding")
from geneformer_embedding.adapter import _example_h5ad_path, build_adapter  # noqa: E402


@pytest.fixture(scope="module")
def adapter():
    return build_adapter()


@pytest.fixture(scope="module")
def example_h5ad_path():
    return _example_h5ad_path()


def test_embedding_has_the_real_model_dimension_and_matches_cell_count(
    adapter, example_h5ad_path
):
    result = adapter.predict({"h5ad_path": example_h5ad_path})
    assert result["output"]["embedding_dim"] == 256
    assert result["output"]["n_cells"] == 20
    assert len(result["output"]["embeddings"]) == 20
    assert all(len(e) == 256 for e in result["output"]["embeddings"])
    assert result["provenance"]["hf_repo"] == "ctheodoris/Geneformer"


def test_embedding_is_deterministic_for_the_same_input(adapter, example_h5ad_path):
    first = adapter.predict({"h5ad_path": example_h5ad_path})["output"]["embeddings"]
    second = adapter.predict({"h5ad_path": example_h5ad_path})["output"]["embeddings"]
    for cell_index, (first_cell, second_cell) in enumerate(zip(first, second)):
        assert first_cell == pytest.approx(second_cell, abs=1e-6), (
            f"cell {cell_index}'s embedding was not reproducible across two runs"
        )


def test_embedding_actually_depends_on_which_cell_not_a_constant_stub(
    adapter, example_h5ad_path
):
    """Not a shape-only check: two different real cells from a real 10x
    Genomics PBMC dataset must produce meaningfully different embeddings,
    or the model isn't actually reading each cell's real expression
    profile.
    """
    embeddings = adapter.predict({"h5ad_path": example_h5ad_path})["output"]["embeddings"]
    cell_0, cell_1 = embeddings[0], embeddings[1]

    max_abs_diff = max(abs(a - b) for a, b in zip(cell_0, cell_1))
    assert max_abs_diff > 0.01, "two different real cells produced near-identical embeddings"
