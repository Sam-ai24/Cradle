from __future__ import annotations

import pytest

from cradle.curation import CurationError, promote_to_curated


def test_promote_to_curated_succeeds_with_full_evidence():
    record = promote_to_curated(
        model_curie="test:1",
        title="Test model",
        evidence_checks={"check_a": True, "check_b": True},
        adapters_used=["engine-a", "engine-b"],
    )
    assert record.tier == "curated"


def test_promote_to_curated_refuses_a_failed_check():
    with pytest.raises(CurationError):
        promote_to_curated(
            model_curie="test:1",
            title="Test model",
            evidence_checks={"check_a": True, "check_b": False},
            adapters_used=["engine-a", "engine-b"],
        )


def test_promote_to_curated_refuses_a_single_adapter():
    with pytest.raises(CurationError):
        promote_to_curated(
            model_curie="test:1",
            title="Test model",
            evidence_checks={"check_a": True},
            adapters_used=["engine-a"],
        )
