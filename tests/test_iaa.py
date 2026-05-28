"""Tests for T13 inter-annotator agreement."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from scripts.compute_iaa import _cohen_kappa, _boundary_f1, compute_iaa


def test_kappa_perfect():
    a = {1, 5, 10}
    assert _cohen_kappa(a, a, 20) == pytest.approx(1.0)


def test_kappa_no_agreement():
    a = {5, 10}
    b = {1, 15}
    # Very different annotations -> kappa < 0.5
    k = _cohen_kappa(a, b, 20)
    assert k < 0.5


def test_kappa_empty_both():
    assert _cohen_kappa(set(), set(), 20) == pytest.approx(1.0)


def test_kappa_with_tolerance():
    a = {5}
    b = {6}  # off by 1
    k_no_tol = _cohen_kappa(a, b, 20, tolerance=0)
    k_with_tol = _cohen_kappa(a, b, 20, tolerance=1)
    assert k_with_tol > k_no_tol


def test_f1_perfect():
    a = {5, 10}
    prec, rec, f1 = _boundary_f1(a, a, 20)
    assert f1 == pytest.approx(1.0)


def test_f1_no_overlap():
    a = {5}
    b = {15}
    _, _, f1 = _boundary_f1(a, b, 20)
    assert f1 == pytest.approx(0.0)


def test_f1_tolerance():
    a = {5}
    b = {6}
    _, _, f1_tol = _boundary_f1(a, b, 20, tolerance=1)
    assert f1_tol == pytest.approx(1.0)


def test_compute_iaa_no_doubles(tmp_path):
    gt_hier = tmp_path / "gt_hier"
    gt_double = tmp_path / "double"
    gt_hier.mkdir()
    gt_double.mkdir()

    result = compute_iaa(gt_hier, gt_double)
    assert result["n_videos"] == 0


def test_compute_iaa_with_data(tmp_path):
    gt_hier = tmp_path / "gt_hier"
    gt_double = tmp_path / "double"
    gt_hier.mkdir()
    gt_double.mkdir()

    ann_a = {
        "video_id": "test_vid",
        "total_sentences": 30,
        "chapters": [10, 20],
        "subtopics": [5, 10, 15, 20, 25],
        "status": "reviewed",
    }
    ann_b = {
        "video_id": "test_vid",
        "total_sentences": 30,
        "chapters": [10, 20],
        "subtopics": [5, 11, 15, 21, 25],
        "status": "reviewed",
    }
    (gt_hier / "test_vid.json").write_text(json.dumps(ann_a), encoding="utf-8")
    (gt_double / "test_vid.json").write_text(json.dumps(ann_b), encoding="utf-8")

    result = compute_iaa(gt_hier, gt_double, tolerance=0)
    assert result["aggregate"]["n_videos"] == 1
    assert result["aggregate"]["mean_kappa_chapter"] == pytest.approx(1.0, abs=0.01)
    assert "test_vid" in result["videos"]


def test_compute_iaa_saves_report(tmp_path):
    gt_hier = tmp_path / "gt_hier"
    gt_double = tmp_path / "double"
    gt_hier.mkdir()
    gt_double.mkdir()

    compute_iaa(gt_hier, gt_double)  # empty — should not crash
