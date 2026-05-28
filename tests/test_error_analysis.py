"""Tests for T31 qualitative error analysis."""
from __future__ import annotations

import pytest
from lecseg.eval.error_analysis import analyse_errors, summarise_errors, BoundaryErrors


def test_perfect_predictions():
    e = analyse_errors([10, 20, 30], [10, 20, 30], n_units=40)
    assert e.precision() == pytest.approx(1.0)
    assert e.recall() == pytest.approx(1.0)
    assert e.f1() == pytest.approx(1.0)
    assert len(e.false_positives) == 0
    assert len(e.false_negatives) == 0


def test_all_false_positives():
    e = analyse_errors([5, 15, 25], [10, 20, 30], n_units=40, tolerance=0)
    assert len(e.false_positives) == 3
    assert e.precision() == pytest.approx(0.0)


def test_all_false_negatives():
    e = analyse_errors([], [10, 20, 30], n_units=40)
    assert len(e.false_negatives) == 3
    assert e.recall() == pytest.approx(0.0)


def test_tolerance_near_miss():
    # Prediction at 11 should match reference at 10 within tolerance=2
    e = analyse_errors([11], [10], n_units=20, tolerance=2)
    assert len(e.true_positives) == 1
    assert len(e.near_misses) == 1
    assert len(e.false_positives) == 0


def test_tolerance_miss():
    # Prediction at 15 should NOT match reference at 10 with tolerance=2
    e = analyse_errors([15], [10], n_units=20, tolerance=2)
    assert len(e.false_positives) == 1
    assert len(e.false_negatives) == 1


def test_partial_match():
    e = analyse_errors([10, 20], [10, 20, 30], n_units=40, tolerance=0)
    assert e.precision() == pytest.approx(1.0)
    assert e.recall() == pytest.approx(2 / 3)


def test_as_dict_keys():
    e = analyse_errors([10], [10], n_units=20)
    d = e.as_dict()
    assert "precision" in d
    assert "recall" in d
    assert "f1" in d
    assert "true_positives" in d
    assert "false_positives" in d
    assert "false_negatives" in d


def test_summarise_errors():
    e1 = analyse_errors([10, 20], [10, 20], n_units=30)
    e2 = analyse_errors([5], [10], n_units=20, tolerance=0)
    summary = summarise_errors([e1, e2])
    assert summary["n_videos"] == 2
    assert summary["total_tp"] == 2
    assert summary["total_fp"] == 1


def test_summarise_empty():
    assert summarise_errors([]) == {}


def test_over_segmentation_flagged():
    # 10 predicted for 3 references = over-segmented
    e = analyse_errors(
        list(range(2, 22, 2)),  # 10 predictions
        [5, 10, 15],
        n_units=25,
        video_id="over_seg_vid",
    )
    summary = summarise_errors([e])
    assert "over_seg_vid" in summary["over_segmented_videos"]


def test_f1_zero_no_overlap():
    e = analyse_errors([5], [15], n_units=20, tolerance=0)
    assert e.f1() == pytest.approx(0.0)
