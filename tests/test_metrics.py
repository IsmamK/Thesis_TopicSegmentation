"""Tests for `lecseg.eval.metrics`. Filled in T22 — these are placeholders."""
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="lecseg.eval.metrics is implemented in T22")
def test_pk_perfect_match(sample_segments_short) -> None:
    from lecseg.eval.metrics import pk

    assert pk(sample_segments_short, sample_segments_short) == 0.0


@pytest.mark.skip(reason="lecseg.eval.metrics is implemented in T22")
def test_windowdiff_bounds(sample_segments_short, sample_segments_predicted) -> None:
    from lecseg.eval.metrics import windowdiff

    val = windowdiff(sample_segments_short, sample_segments_predicted)
    assert 0.0 <= val <= 1.0


@pytest.mark.skip(reason="lecseg.eval.metrics is implemented in T22")
def test_boundary_similarity_symmetric(sample_segments_short, sample_segments_predicted) -> None:
    from lecseg.eval.metrics import boundary_similarity

    a = boundary_similarity(sample_segments_short, sample_segments_predicted)
    b = boundary_similarity(sample_segments_predicted, sample_segments_short)
    assert abs(a - b) < 1e-6
