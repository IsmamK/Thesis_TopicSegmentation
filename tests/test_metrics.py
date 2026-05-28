"""Tests for T22 metrics library — lecseg.metrics."""
from __future__ import annotations

import pytest
from lecseg.metrics import (
    evaluate, pk, wd, boundary_similarity, tolerance_f1, h_wd
)


def test_perfect():
    ref = [10, 20, 30]
    s = evaluate(ref, ref, n_units=40)
    assert s.pk == 0.0
    assert s.wd == 0.0
    assert s.boundary_similarity == 1.0
    assert s.f1 == 1.0
    assert s.precision == 1.0
    assert s.recall == 1.0


def test_no_hypothesis():
    ref = [10, 20]
    s = evaluate([], ref, n_units=30)
    assert s.pk > 0.0
    assert s.wd > 0.0
    assert s.f1 == 0.0
    assert s.recall == 0.0


def test_no_reference():
    s = evaluate([10, 20], [], n_units=30)
    assert s.f1 == 0.0
    assert s.precision == 0.0


def test_both_empty():
    s = evaluate([], [], n_units=30)
    assert s.boundary_similarity == 1.0
    assert s.f1 == 1.0


def test_tolerance_f1_within_window():
    prec, rec, f1 = tolerance_f1([11], [10], n_units=20, tolerance=2)
    assert f1 == 1.0


def test_tolerance_f1_outside_window():
    prec, rec, f1 = tolerance_f1([15], [10], n_units=20, tolerance=2)
    assert f1 == 0.0


def test_pk_bounds():
    ref = [5, 10, 15, 20, 25]
    hyp = [3, 8, 13, 18, 23]
    score = pk(hyp, ref, n_units=30)
    assert 0.0 <= score <= 1.0


def test_wd_perfect():
    ref = [10, 20]
    assert wd(ref, ref, n_units=30) == 0.0


def test_wd_bounds():
    ref = [10, 20]
    hyp = [5, 25]
    score = wd(hyp, ref, n_units=30)
    assert 0.0 <= score <= 1.0


def test_boundary_similarity_partial():
    ref = [10, 20, 30]
    hyp = [10, 20]
    score = boundary_similarity(hyp, ref, n_units=40)
    assert 0.0 < score < 1.0


def test_h_wd_perfect():
    ref_ch = [20, 40]
    ref_sub = [10, 15, 25, 35]
    assert h_wd(ref_ch, ref_ch, ref_sub, ref_sub, n_units=60) == 0.0


def test_evaluate_with_subtopics():
    ref_ch = [20, 40]
    ref_sub = [10, 30, 50]
    s = evaluate(ref_ch, ref_ch, n_units=60,
                 hyp_subtopic=ref_sub, ref_subtopic=ref_sub)
    assert s.h_wd == 0.0
    assert s.pk == 0.0


def test_as_dict_excludes_none():
    s = evaluate([10], [10], n_units=20)
    assert "h_wd" not in s.as_dict()


def test_as_dict_includes_h_wd():
    s = evaluate([10], [10], n_units=20,
                 hyp_subtopic=[5], ref_subtopic=[5])
    assert "h_wd" in s.as_dict()
    assert s.as_dict()["h_wd"] == 0.0
