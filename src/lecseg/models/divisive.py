"""Divisive top-down clustering segmenter (TreeSeg-style).

Greedy max-heap divisive segmenter. At every step the segment whose best
internal split maximises cosine dissimilarity between the means of its two
halves is popped and split. Repeats until n_segments-1 boundaries exist.

Reference: Gklezakos et al. 2024, "TreeSeg" (arxiv:2407.12028).
"""
from __future__ import annotations

import heapq
import numpy as np


def _cos_dissim(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return 1.0 - float(a @ b) / (na * nb)


def _best_split(cumsum: np.ndarray, start: int, end: int) -> tuple[int, float]:
    """Return (split_index, score) maximising dissimilarity in [start, end).

    cumsum: (N+1, D) cumulative sum so that mean(vecs[a:b]) =
            (cumsum[b]-cumsum[a]) / (b-a).
    """
    best_s = -1
    best_score = -1.0
    for s in range(start + 1, end):
        left_n = s - start
        right_n = end - s
        if left_n <= 0 or right_n <= 0:
            continue
        left_mean = (cumsum[s] - cumsum[start]) / left_n
        right_mean = (cumsum[end] - cumsum[s]) / right_n
        score = _cos_dissim(left_mean, right_mean)
        if score > best_score:
            best_score = score
            best_s = s
    return best_s, best_score


def divisive_seg(
    vecs: np.ndarray,
    n_segments: int,
    return_scores: bool = False,
) -> list[int] | tuple[list[int], dict[int, float]]:
    """Divisive top-down cosine clustering.

    Args:
        vecs:        (N, D) embedding matrix.
        n_segments:  target number of segments (>= 2).
        return_scores: if True also return {boundary: dissimilarity_score}.

    Returns:
        Sorted list of boundary indices (1-based gap indices, in [1, N-1]).
        If return_scores, returns (boundaries, {b: score}).
    """
    N = len(vecs)
    if N < 2 or n_segments < 2:
        return ([], {}) if return_scores else []

    # Edge case: too short — fall back to cosine_seg
    if N < 4:
        from lecseg.baselines.neural import cosine_seg
        b = cosine_seg(vecs, n_segments=n_segments)
        return (b, {x: 0.0 for x in b}) if return_scores else b

    # Cumulative sums for O(1) mean computation
    cumsum = np.zeros((N + 1, vecs.shape[1]), dtype=np.float64)
    cumsum[1:] = np.cumsum(vecs.astype(np.float64), axis=0)

    # Initial split of [0, N)
    s0, score0 = _best_split(cumsum, 0, N)
    if s0 < 0:
        return ([], {}) if return_scores else []

    # Max-heap via negative score. Tiebreak by (start, end) for determinism.
    heap: list = []
    counter = 0
    heapq.heappush(heap, (-score0, counter, 0, N, s0))
    counter += 1

    boundaries: list[int] = []
    scores: dict[int, float] = {}
    target_b = max(0, n_segments - 1)

    while heap and len(boundaries) < target_b:
        neg_score, _, start, end, split = heapq.heappop(heap)
        score = -neg_score
        if split <= start or split >= end:
            continue
        boundaries.append(split)
        scores[split] = score

        # Left child [start, split)
        if split - start >= 2:
            ls, lscore = _best_split(cumsum, start, split)
            if ls > start:
                heapq.heappush(heap, (-lscore, counter, start, split, ls))
                counter += 1
        # Right child [split, end)
        if end - split >= 2:
            rs, rscore = _best_split(cumsum, split, end)
            if rs > split:
                heapq.heappush(heap, (-rscore, counter, split, end, rs))
                counter += 1

    boundaries = sorted(b for b in boundaries if 0 < b < N)
    return (boundaries, scores) if return_scores else boundaries


def _best_split_constrained(
    cumsum: np.ndarray, start: int, end: int, min_seg: int
) -> tuple[int, float]:
    """Like _best_split but only considers splits that create segments >= min_seg."""
    best_s = -1
    best_score = -1.0
    for s in range(start + min_seg, end - min_seg + 1):
        left_n = s - start
        right_n = end - s
        if left_n < min_seg or right_n < min_seg:
            continue
        left_mean = (cumsum[s] - cumsum[start]) / left_n
        right_mean = (cumsum[end] - cumsum[s]) / right_n
        score = _cos_dissim(left_mean, right_mean)
        if score > best_score:
            best_score = score
            best_s = s
    return best_s, best_score


def divisive_seg_constrained(
    vecs: np.ndarray,
    n_segments: int,
    min_seg: int = 10,
) -> list[int]:
    """Constrained divisive segmentation — segments are always >= min_seg long.

    Identical to divisive_seg but only considers split positions that result
    in both sub-segments having at least min_seg sentences. This avoids the
    post-hoc filtering step and finds the best-scoring valid partition directly.
    """
    N = len(vecs)
    if N < 2 or n_segments < 2 or N < min_seg * 2:
        return []

    cumsum = np.zeros((N + 1, vecs.shape[1]), dtype=np.float64)
    cumsum[1:] = np.cumsum(vecs.astype(np.float64), axis=0)

    s0, score0 = _best_split_constrained(cumsum, 0, N, min_seg)
    if s0 < 0:
        return []

    heap: list = []
    counter = 0
    heapq.heappush(heap, (-score0, counter, 0, N, s0))
    counter += 1

    boundaries: list[int] = []
    target_b = max(0, n_segments - 1)

    while heap and len(boundaries) < target_b:
        neg_score, _, start, end, split = heapq.heappop(heap)
        if split <= start or split >= end:
            continue
        boundaries.append(split)

        if split - start >= min_seg * 2:
            ls, lscore = _best_split_constrained(cumsum, start, split, min_seg)
            if ls > start:
                heapq.heappush(heap, (-lscore, counter, start, split, ls))
                counter += 1
        if end - split >= min_seg * 2:
            rs, rscore = _best_split_constrained(cumsum, split, end, min_seg)
            if rs > split:
                heapq.heappush(heap, (-rscore, counter, split, end, rs))
                counter += 1

    return sorted(b for b in boundaries if 0 < b < N)
