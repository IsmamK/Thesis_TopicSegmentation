"""Tests for postprocess utilities."""
import pytest
from lecseg.postprocess import min_segment_length, boundary_nms, apply_postprocessing
import numpy as np


def test_min_segment_length_basic():
    # boundaries [5, 10, 15] with N=20, min=6: [10] would create [10, 5, 5] — 5 < 6
    result = min_segment_length([5, 10, 15], None, n_sentences=20, min_sentences=6)
    all_bounds = [0] + result + [20]
    lengths = [all_bounds[i+1] - all_bounds[i] for i in range(len(all_bounds)-1)]
    assert all(l >= 6 for l in lengths)


def test_min_segment_length_all_ok():
    result = min_segment_length([10, 20, 30], None, n_sentences=40, min_sentences=5)
    assert result == [10, 20, 30]


def test_min_segment_length_empty():
    assert min_segment_length([], None, 20, 5) == []


def test_boundary_nms_removes_nearby():
    # [10, 12] are within window=5, keep only the higher-scored one
    scores = [0.9, 0.3]
    result = boundary_nms([10, 12], scores, window_sentences=5)
    assert 10 in result
    assert 12 not in result


def test_boundary_nms_keeps_distant():
    scores = [0.9, 0.8]
    result = boundary_nms([10, 20], scores, window_sentences=5)
    assert sorted(result) == [10, 20]


def test_boundary_nms_empty():
    assert boundary_nms([], None, 5) == []


def test_apply_postprocessing_pipeline():
    bounds = [3, 5, 15, 25, 30, 35]
    scores = np.array([0.9, 0.3, 0.8, 0.7, 0.4, 0.6])
    result = apply_postprocessing(bounds, scores, n_sentences=50,
                                  min_sentences=8, nms_window=4)
    # All resulting segments should be >= 8 sentences
    all_bounds = [0] + result + [50]
    lengths = [all_bounds[i+1] - all_bounds[i] for i in range(len(all_bounds)-1)]
    assert all(l >= 8 for l in lengths), f"Short segment: {lengths}"


def test_apply_postprocessing_empty():
    assert apply_postprocessing([], None, 50) == []
