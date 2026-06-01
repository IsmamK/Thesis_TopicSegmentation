"""
Post-processing utilities for boundary prediction.

- min_segment_length: remove boundaries that create segments shorter than min_sentences
- boundary_nms: non-maximum suppression to merge nearby boundaries
"""
from __future__ import annotations
import numpy as np


def min_segment_length(
    boundaries: list[int],
    scores: list[float] | np.ndarray | None,
    n_sentences: int,
    min_sentences: int = 8,
) -> list[int]:
    """
    Remove boundaries that would create a segment shorter than min_sentences.

    Keeps the strongest boundaries first (by score), then rejects any boundary
    that would create a too-short segment.

    Args:
        boundaries:    sorted list of 1-based boundary indices
        scores:        per-boundary score (higher = stronger). If None, keeps in order.
        n_sentences:   total number of sentences
        min_sentences: minimum allowed segment length in sentences

    Returns:
        Filtered, sorted boundary list.
    """
    if not boundaries:
        return []

    bounds = sorted(set(int(b) for b in boundaries if 0 < b < n_sentences))
    if scores is not None:
        score_map = {b: float(s) for b, s in zip(boundaries, scores)}
        bounds_with_scores = sorted(bounds, key=lambda b: -score_map.get(b, 0.0))
    else:
        bounds_with_scores = bounds  # keep original order

    accepted: set[int] = set()

    for b in bounds_with_scores:
        # Build tentative boundary set including this candidate
        tentative = sorted(accepted | {b})
        all_bounds = [0] + tentative + [n_sentences]
        lengths = [all_bounds[i+1] - all_bounds[i] for i in range(len(all_bounds)-1)]
        if all(l >= min_sentences for l in lengths):
            accepted.add(b)

    return sorted(accepted)


def boundary_nms(
    boundaries: list[int],
    scores: list[float] | np.ndarray | None,
    window_sentences: int = 5,
) -> list[int]:
    """
    Non-maximum suppression: if two boundaries are within window_sentences of each other,
    keep only the stronger one.

    Args:
        boundaries:        sorted list of 1-based boundary indices
        scores:            per-boundary strength score (higher = keep). If None, keep first.
        window_sentences:  suppression window radius

    Returns:
        Filtered, sorted boundary list.
    """
    if not boundaries:
        return []

    bounds = sorted(set(int(b) for b in boundaries))
    if scores is not None:
        score_map = {b: float(s) for b, s in zip(boundaries, scores)}
    else:
        score_map = {b: 1.0 for b in bounds}

    # Sort by descending score
    by_score = sorted(bounds, key=lambda b: -score_map.get(b, 0.0))

    suppressed: set[int] = set()
    kept: list[int] = []

    for b in by_score:
        if b in suppressed:
            continue
        kept.append(b)
        # Suppress nearby boundaries
        for nb in bounds:
            if nb != b and abs(nb - b) <= window_sentences:
                suppressed.add(nb)

    return sorted(kept)


def apply_postprocessing(
    boundaries: list[int],
    gap_scores: np.ndarray | None,
    n_sentences: int,
    min_sentences: int = 8,
    nms_window: int = 5,
) -> list[int]:
    """
    Apply both NMS and min-segment-length filtering in sequence.

    First NMS (remove duplicate nearby boundaries), then min-length check.
    """
    if not boundaries:
        return []

    if gap_scores is not None:
        scores = [float(gap_scores[b-1]) if 0 < b <= len(gap_scores) else 0.0
                  for b in boundaries]
    else:
        scores = None

    # Step 1: NMS
    bounds = boundary_nms(boundaries, scores, window_sentences=nms_window)

    # Recompute scores for remaining boundaries
    if gap_scores is not None:
        scores2 = [float(gap_scores[b-1]) if 0 < b <= len(gap_scores) else 0.0
                   for b in bounds]
    else:
        scores2 = None

    # Step 2: Min segment length
    bounds = min_segment_length(bounds, scores2, n_sentences, min_sentences=min_sentences)

    return bounds
