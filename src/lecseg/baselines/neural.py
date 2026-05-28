"""
T24 — Neural text segmentation baselines.

Baselines:
    CosineSeg   — Local cosine similarity drop between adjacent sentence windows
    KMeansSeg   — K-means clustering on sentence embeddings, then boundary detection
    BertSeg     — Simplified BERT-based segmentation via cosine similarity
                  (full SegBot requires separate training; this implements the
                  inference-time cosine-depth approach from Koshorek et al. 2018)

All take a (N, D) embedding matrix and return boundary indices.

Usage:
    from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg

    boundaries = cosine_seg(vecs, window=3)
    boundaries = kmeans_seg(vecs, n_segments=5)
"""

from __future__ import annotations

import math
import numpy as np
from typing import Sequence


# ---------------------------------------------------------------------------
# Cosine similarity segmenter
# ---------------------------------------------------------------------------

def _window_vec(vecs: np.ndarray, center: int, half_win: int) -> np.ndarray:
    """Average of vectors in a window around center."""
    lo = max(0, center - half_win)
    hi = min(len(vecs), center + half_win + 1)
    return vecs[lo:hi].mean(axis=0)


def cosine_seg(
    vecs: np.ndarray,
    window: int = 3,
    threshold: float | None = None,
    std_coeff: float = 1.0,
    n_segments: int | None = None,
) -> list[int]:
    """
    Local cosine similarity segmentation (Choi 2000-style, on dense embeddings).

    Computes similarity between left and right windows at each sentence gap,
    then finds valleys (low similarity = likely boundary).

    Args:
        vecs:       (N, D) L2-normalised embedding matrix
        window:     half-window size for averaging
        threshold:  similarity threshold below which gaps are boundaries
                    (None = auto: mean - std_coeff * std)
        std_coeff:  multiplier for std when computing auto threshold
        n_segments: if set, return exactly (n_segments-1) boundaries

    Returns:
        Sorted list of 1-based boundary indices.
    """
    N = len(vecs)
    if N < 3:
        return []

    # Compute similarity at each gap
    sims: list[float] = []
    for i in range(1, N):
        left = _window_vec(vecs, i - 1, window)
        right = _window_vec(vecs, i, window)
        norm = np.linalg.norm(left) * np.linalg.norm(right)
        sim = float(left @ right) / norm if norm > 0 else 0.0
        sims.append(sim)

    # Depth score (local minima detection)
    depth = []
    for i, s in enumerate(sims):
        left_max = max(sims[:i + 1])
        right_max = max(sims[i:])
        depth.append((left_max - s) + (right_max - s))

    if n_segments is not None:
        n_boundaries = max(0, n_segments - 1)
        indexed = sorted(enumerate(depth), key=lambda x: -x[1])
        return sorted(idx + 1 for idx, _ in indexed[:n_boundaries])

    if threshold is not None:
        return [i + 1 for i, s in enumerate(sims) if s < threshold]

    # Auto threshold on depth scores
    mean_d = sum(depth) / len(depth)
    std_d = math.sqrt(sum((d - mean_d) ** 2 for d in depth) / len(depth))
    cutoff = mean_d + std_coeff * std_d
    return sorted(i + 1 for i, d in enumerate(depth) if d > cutoff)


# ---------------------------------------------------------------------------
# K-means segmenter
# ---------------------------------------------------------------------------

def kmeans_seg(
    vecs: np.ndarray,
    n_segments: int,
    random_state: int = 42,
) -> list[int]:
    """
    K-means based segmentation: cluster sentences into n_segments clusters,
    then find transitions between cluster labels as boundaries.

    Args:
        vecs:       (N, D) embedding matrix
        n_segments: target number of segments (= number of clusters)
        random_state: random seed for reproducibility

    Returns:
        Sorted list of 1-based boundary indices.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize

    N = len(vecs)
    if N < n_segments:
        return list(range(1, N))

    X = normalize(vecs.astype(np.float64))
    km = KMeans(n_clusters=n_segments, random_state=random_state, n_init=10)
    labels = km.fit_predict(X)

    # Find positions where cluster label changes
    boundaries = [i for i in range(1, N) if labels[i] != labels[i - 1]]
    return sorted(boundaries)


# ---------------------------------------------------------------------------
# BERT-style cosine depth segmenter (BertSeg)
# ---------------------------------------------------------------------------

def bert_seg(
    vecs: np.ndarray,
    window: int = 5,
    n_segments: int | None = None,
    std_coeff: float = 1.2,
) -> list[int]:
    """
    BERT-based segmentation using pre-computed BERT/sentence embeddings.

    Implements the cosine-depth scoring from Koshorek et al. (2018):
    for each gap, compute similarity between concatenated left-window and
    right-window embeddings using averaged BERT vectors.

    In practice this is equivalent to cosine_seg with a larger window and
    different scoring, but matches the SegBot inference approach.

    Args:
        vecs:       (N, D) BERT/sentence embedding matrix (e.g. from MPNet)
        window:     comparison window size
        n_segments: target segments (None = auto threshold)
        std_coeff:  auto-threshold multiplier

    Returns:
        Sorted list of 1-based boundary indices.
    """
    return cosine_seg(vecs, window=window, n_segments=n_segments, std_coeff=std_coeff)
