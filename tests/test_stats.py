"""Tests for T30 bootstrap CIs and Wilcoxon tests."""
from __future__ import annotations

import pytest
from lecseg.eval.stats import bootstrap_ci, wilcoxon_test, compare_methods


def test_bootstrap_ci_shape():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    point, lo, hi = bootstrap_ci(values)
    assert lo <= point <= hi


def test_bootstrap_ci_mean():
    values = [0.3] * 10  # constant -> mean = 0.3
    point, _, _ = bootstrap_ci(values)
    assert point == pytest.approx(0.3, abs=1e-4)


def test_bootstrap_ci_empty():
    assert bootstrap_ci([]) == (0.0, 0.0, 0.0)


def test_bootstrap_ci_interval_width():
    # More spread -> wider interval
    tight = [0.5] * 20
    spread = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] * 2
    _, lo_t, hi_t = bootstrap_ci(tight)
    _, lo_s, hi_s = bootstrap_ci(spread)
    assert (hi_s - lo_s) > (hi_t - lo_t)


def test_wilcoxon_identical():
    # Identical distributions -> high p-value (no difference)
    a = [0.1, 0.2, 0.3, 0.4, 0.5]
    p = wilcoxon_test(a, a)
    assert p == 1.0


def test_wilcoxon_different():
    # Clearly different: a all low, b all high -> significant
    a = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    b = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
    p = wilcoxon_test(a, b)
    assert p < 0.05


def test_wilcoxon_p_range():
    a = [0.1, 0.3, 0.5, 0.2, 0.4]
    b = [0.2, 0.4, 0.6, 0.3, 0.5]
    p = wilcoxon_test(a, b)
    assert 0 <= p <= 1


def test_wilcoxon_length_mismatch():
    with pytest.raises(ValueError):
        wilcoxon_test([0.1, 0.2], [0.1])


def test_compare_methods():
    # Method A (baseline) has higher Pk (worse)
    # Method B (novel) has lower Pk (better)
    results = {
        "baseline": {
            "v1": {"pk": 0.4, "wd": 0.45, "f1": 0.5, "boundary_similarity": 0.6},
            "v2": {"pk": 0.35, "wd": 0.4, "f1": 0.55, "boundary_similarity": 0.65},
        },
        "novel": {
            "v1": {"pk": 0.2, "wd": 0.25, "f1": 0.7, "boundary_similarity": 0.8},
            "v2": {"pk": 0.15, "wd": 0.2, "f1": 0.75, "boundary_similarity": 0.85},
        },
    }
    report = compare_methods(results, baseline="baseline", novel="novel", n_bootstrap=100)
    assert "metrics" in report
    assert report["n_videos"] == 2
    # Novel should improve Pk (lower is better)
    pk_cmp = report["metrics"]["pk"]
    assert pk_cmp["novel_mean"] < pk_cmp["baseline_mean"]
    assert pk_cmp["improves"] is True


def test_compare_no_common_videos():
    results = {
        "a": {"v1": {"pk": 0.3}},
        "b": {"v2": {"pk": 0.2}},
    }
    report = compare_methods(results, baseline="a", novel="b")
    assert "error" in report
