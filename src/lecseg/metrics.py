"""
T22 — Segmentation evaluation metrics.

Metrics implemented:
    pk          — Pk (Beeferman 1999)
    wd          — WindowDiff (Pevzner & Hearst 2002)
    boundary_similarity  — B (Fournier 2013)
    f1          — Tolerance-F1 (precision/recall with boundary tolerance window)
    h_wd        — Hierarchical WindowDiff (subtopic-aware)

All functions accept boundaries as either:
    - list[float]  — boundary timestamps in seconds
    - list[int]    — boundary sentence indices

Usage:
    from lecseg.metrics import evaluate
    scores = evaluate(predicted_boundaries, reference_boundaries, duration_sec=3600)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SegmentationScores:
    pk: float
    wd: float
    boundary_similarity: float
    f1: float
    precision: float
    recall: float
    h_wd: float | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def __str__(self) -> str:
        lines = [f"  {k:20s}: {v:.4f}" for k, v in self.as_dict().items()]
        return "SegmentationScores:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_binary(boundaries: list[float | int], n_units: int) -> list[int]:
    """Convert boundary list to binary sequence of length n_units - 1."""
    boundary_set = set(int(b) for b in boundaries)
    return [1 if i in boundary_set else 0 for i in range(1, n_units)]


def _boundaries_to_masses(boundaries: list[int], total: int) -> list[int]:
    """Convert sorted boundary indices to segment mass list."""
    sorted_b = sorted(set(int(b) for b in boundaries if 0 < b < total))
    positions = [0] + sorted_b + [total]
    return [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]


def _default_k(masses: list[int]) -> int:
    """Standard k = half average segment size."""
    avg = sum(masses) / len(masses) if masses else 1
    return max(1, int(round(avg / 2)))


# ---------------------------------------------------------------------------
# Pk
# ---------------------------------------------------------------------------

def pk(
    hypothesis: list[float | int],
    reference: list[float | int],
    n_units: int,
    k: int | None = None,
    boundary: int = 1,
) -> float:
    """
    Pk error metric (lower is better, 0 = perfect).
    n_units: total number of units (sentences or seconds).
    """
    ref_masses = _boundaries_to_masses(reference, n_units)
    hyp_masses = _boundaries_to_masses(hypothesis, n_units)

    if k is None:
        k = _default_k(ref_masses)

    ref_bin = _to_binary(reference, n_units)
    hyp_bin = _to_binary(hypothesis, n_units)

    # Build cumulative segment index arrays
    def _cum(masses: list[int]) -> list[int]:
        result, idx = [], 0
        for m in masses:
            result.extend([idx] * m)
            idx += 1
        return result

    ref_cum = _cum(ref_masses)
    hyp_cum = _cum(hyp_masses)

    errors = total = 0
    for i in range(n_units - k):
        ref_same = ref_cum[i] == ref_cum[i + k]
        hyp_same = hyp_cum[i] == hyp_cum[i + k]
        if ref_same != hyp_same:
            errors += 1
        total += 1

    return errors / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# WindowDiff
# ---------------------------------------------------------------------------

def wd(
    hypothesis: list[float | int],
    reference: list[float | int],
    n_units: int,
    k: int | None = None,
) -> float:
    """
    WindowDiff (lower is better, 0 = perfect).
    """
    ref_masses = _boundaries_to_masses(reference, n_units)
    if k is None:
        k = _default_k(ref_masses)

    ref_bin = _to_binary(reference, n_units)
    hyp_bin = _to_binary(hypothesis, n_units)

    errors = total = 0
    for i in range(n_units - k):
        ref_count = sum(ref_bin[i:i + k])
        hyp_count = sum(hyp_bin[i:i + k])
        if ref_count != hyp_count:
            errors += 1
        total += 1

    return errors / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Boundary Similarity (B)
# ---------------------------------------------------------------------------

def boundary_similarity(
    hypothesis: list[float | int],
    reference: list[float | int],
    n_units: int,
    n: int = 2,
) -> float:
    """
    Boundary Similarity score (higher is better, 1 = perfect).
    n: substitution penalty neighbourhood size.
    """
    ref_set = set(int(b) for b in reference if 0 < b < n_units)
    hyp_set = set(int(b) for b in hypothesis if 0 < b < n_units)

    if not ref_set and not hyp_set:
        return 1.0
    if not ref_set or not hyp_set:
        return 0.0

    def _boundary_score(b: int, candidates: set[int]) -> float:
        if b in candidates:
            return 1.0
        for d in range(1, n + 1):
            if (b - d) in candidates or (b + d) in candidates:
                return 1.0 - (d / (n + 1))
        return 0.0

    ref_score = sum(_boundary_score(b, hyp_set) for b in ref_set) / len(ref_set)
    hyp_score = sum(_boundary_score(b, ref_set) for b in hyp_set) / len(hyp_set)
    return (ref_score + hyp_score) / 2


# ---------------------------------------------------------------------------
# Tolerance-F1
# ---------------------------------------------------------------------------

def tolerance_f1(
    hypothesis: list[float | int],
    reference: list[float | int],
    n_units: int,
    tolerance: int = 2,
) -> tuple[float, float, float]:
    """
    F1 with tolerance window (returns precision, recall, f1).
    A predicted boundary counts as TP if within `tolerance` units of a reference boundary.
    """
    ref_set = set(int(b) for b in reference if 0 < b < n_units)
    hyp_set = set(int(b) for b in hypothesis if 0 < b < n_units)

    if not ref_set and not hyp_set:
        return 1.0, 1.0, 1.0
    if not hyp_set:
        return 0.0, 0.0, 0.0
    if not ref_set:
        return 0.0, 0.0, 0.0

    matched_ref = set()
    tp = 0
    for h in hyp_set:
        for d in range(-tolerance, tolerance + 1):
            if (h + d) in ref_set and (h + d) not in matched_ref:
                tp += 1
                matched_ref.add(h + d)
                break

    precision = tp / len(hyp_set)
    recall = tp / len(ref_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ---------------------------------------------------------------------------
# Hierarchical WindowDiff (subtopic-aware)
# ---------------------------------------------------------------------------

def h_wd(
    hyp_chapter: list[float | int],
    ref_chapter: list[float | int],
    hyp_subtopic: list[float | int],
    ref_subtopic: list[float | int],
    n_units: int,
    k: int | None = None,
    alpha: float = 0.5,
) -> float:
    """
    Hierarchical WindowDiff — weighted combination of chapter and subtopic WD.
    alpha: weight for chapter-level WD (1-alpha for subtopic).
    Lower is better.
    """
    wd_chapter = wd(hyp_chapter, ref_chapter, n_units, k)
    wd_subtopic = wd(hyp_subtopic, ref_subtopic, n_units, k)
    return alpha * wd_chapter + (1 - alpha) * wd_subtopic


# ---------------------------------------------------------------------------
# Combined evaluator
# ---------------------------------------------------------------------------

def evaluate(
    hypothesis: list[float | int],
    reference: list[float | int],
    n_units: int,
    tolerance: int = 2,
    k: int | None = None,
    hyp_subtopic: list[float | int] | None = None,
    ref_subtopic: list[float | int] | None = None,
) -> SegmentationScores:
    """
    Run all metrics and return a SegmentationScores object.

    Args:
        hypothesis:    predicted boundary positions (sentence indices or seconds)
        reference:     ground-truth boundary positions
        n_units:       total number of units (sentences or seconds)
        tolerance:     tolerance window for F1 (default 2 units)
        k:             window size for Pk/WD (default = half avg segment size)
        hyp_subtopic:  predicted subtopic boundaries (for H-WD)
        ref_subtopic:  reference subtopic boundaries (for H-WD)
    """
    _pk = pk(hypothesis, reference, n_units, k)
    _wd = wd(hypothesis, reference, n_units, k)
    _bs = boundary_similarity(hypothesis, reference, n_units)
    prec, rec, _f1 = tolerance_f1(hypothesis, reference, n_units, tolerance)

    _h_wd = None
    if hyp_subtopic is not None and ref_subtopic is not None:
        _h_wd = h_wd(hypothesis, reference, hyp_subtopic, ref_subtopic, n_units, k)

    return SegmentationScores(
        pk=_pk,
        wd=_wd,
        boundary_similarity=_bs,
        f1=_f1,
        precision=prec,
        recall=rec,
        h_wd=_h_wd,
    )
