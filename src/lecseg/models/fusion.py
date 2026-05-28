"""
T25 / N2 — Reliability-Weighted Fusion module.

Fuses multiple modality scores (text similarity, visual coherence, prosody)
into a single boundary probability using learned or heuristic reliability weights.

The reliability weight for modality m is estimated as:
    w_m = exp(-H_m / log2(N))
where H_m is the entropy of the modality's boundary score distribution
(low entropy = high confidence = high reliability weight).

This is the core novel contribution: unlike simple averaging or fixed weights,
RWF adapts to per-video modality reliability.

Usage:
    from lecseg.models.fusion import ReliabilityWeightedFusion

    rwf = ReliabilityWeightedFusion(method="entropy")
    boundaries = rwf.predict(
        modality_scores={"text": text_scores, "visual": visual_scores},
        n_sentences=N,
        n_segments=5,
    )
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Literal


def _entropy(scores: np.ndarray, eps: float = 1e-9) -> float:
    """Normalised Shannon entropy of a score distribution (0=deterministic, 1=uniform)."""
    p = scores - scores.min()
    total = p.sum()
    if total < eps:
        return 1.0
    p = p / total + eps
    p = p / p.sum()
    h = -float(np.sum(p * np.log2(p)))
    h_max = math.log2(len(scores)) if len(scores) > 1 else 1.0
    return h / h_max if h_max > 0 else 0.0


def _reliability_weight(scores: np.ndarray) -> float:
    """Reliability weight = exp(-entropy)."""
    h = _entropy(scores)
    return math.exp(-h)


def _softmax(x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64) / temperature
    e = np.exp(x - x.max())
    return (e / e.sum()).astype(np.float32)


@dataclass
class ReliabilityWeightedFusion:
    """
    Fuse boundary scores from multiple modalities using reliability weighting.

    Args:
        method:      'entropy' (auto-estimated) | 'uniform' | 'fixed'
        fixed_weights: {modality: weight} used when method='fixed'
        temperature:  temperature for softmax boundary prediction
    """

    method: Literal["entropy", "uniform", "fixed"] = "entropy"
    fixed_weights: dict[str, float] = field(default_factory=dict)
    temperature: float = 1.0

    def compute_weights(self, modality_scores: dict[str, np.ndarray]) -> dict[str, float]:
        """Compute per-modality reliability weights."""
        if self.method == "fixed":
            total = sum(self.fixed_weights.get(m, 1.0) for m in modality_scores)
            return {m: self.fixed_weights.get(m, 1.0) / total for m in modality_scores}

        if self.method == "uniform":
            n = len(modality_scores)
            return {m: 1.0 / n for m in modality_scores}

        # entropy method
        raw = {m: _reliability_weight(s) for m, s in modality_scores.items()}
        total = sum(raw.values()) or 1.0
        return {m: w / total for m, w in raw.items()}

    def fuse(self, modality_scores: dict[str, np.ndarray]) -> np.ndarray:
        """
        Fuse gap scores from multiple modalities.

        Args:
            modality_scores: {name: array of shape (N_gaps,)} boundary scores per modality

        Returns:
            Fused boundary score array of shape (N_gaps,), normalised to [0, 1].
        """
        if not modality_scores:
            raise ValueError("No modality scores provided")

        lengths = [len(s) for s in modality_scores.values()]
        if len(set(lengths)) > 1:
            raise ValueError(f"Modality score lengths mismatch: {lengths}")

        weights = self.compute_weights(modality_scores)
        n = lengths[0]
        fused = np.zeros(n, dtype=np.float64)

        for m, scores in modality_scores.items():
            # Normalise each modality's scores to [0, 1]
            s = np.asarray(scores, dtype=np.float64)
            rng = s.max() - s.min()
            if rng > 0:
                s = (s - s.min()) / rng
            fused += weights[m] * s

        # Normalise to [0, 1]
        rng = fused.max() - fused.min()
        if rng > 0:
            fused = (fused - fused.min()) / rng

        return fused.astype(np.float32)

    def predict(
        self,
        modality_scores: dict[str, np.ndarray],
        n_sentences: int,
        n_segments: int | None = None,
        threshold: float | None = None,
        std_coeff: float = 1.0,
    ) -> list[int]:
        """
        Predict boundary indices from modality boundary scores.

        Args:
            modality_scores: {name: (N_sentences-1,) gap score arrays}
            n_sentences:     total sentence count
            n_segments:      target number of segments (None = threshold-based)
            threshold:       boundary score threshold (None = auto)
            std_coeff:       std multiplier for auto threshold

        Returns:
            Sorted list of 1-based boundary sentence indices.
        """
        fused = self.fuse(modality_scores)

        if n_segments is not None:
            n_boundaries = max(0, n_segments - 1)
            indexed = sorted(enumerate(fused), key=lambda x: -x[1])
            return sorted(idx + 1 for idx, _ in indexed[:n_boundaries]
                          if 0 < idx + 1 < n_sentences)

        if threshold is not None:
            return [i + 1 for i, s in enumerate(fused) if s > threshold]

        # Auto threshold: mean + std_coeff * std
        mean = float(fused.mean())
        std = float(fused.std())
        cutoff = mean + std_coeff * std
        return sorted(i + 1 for i, s in enumerate(fused)
                      if s > cutoff and 0 < i + 1 < n_sentences)

    def reliability_report(self, modality_scores: dict[str, np.ndarray]) -> dict:
        """Return a dict of per-modality entropy, reliability weight, and effective weight."""
        weights = self.compute_weights(modality_scores)
        return {
            m: {
                "entropy": round(_entropy(s), 4),
                "raw_reliability": round(_reliability_weight(s), 4),
                "effective_weight": round(weights[m], 4),
            }
            for m, s in modality_scores.items()
        }


def gap_scores_from_vecs(vecs: np.ndarray, window: int = 3) -> np.ndarray:
    """
    Compute boundary gap scores (cosine dissimilarity) from embedding matrix.
    Returns array of shape (N-1,) — high values = likely boundary.
    """
    N = len(vecs)
    if N < 2:
        return np.zeros(max(0, N - 1), dtype=np.float32)

    from lecseg.baselines.neural import _window_vec

    scores = np.zeros(N - 1, dtype=np.float32)
    for i in range(1, N):
        left = _window_vec(vecs, i - 1, window)
        right = _window_vec(vecs, i, window)
        norm = np.linalg.norm(left) * np.linalg.norm(right)
        sim = float(left @ right) / norm if norm > 0 else 0.0
        scores[i - 1] = 1.0 - sim  # dissimilarity = boundary strength

    return scores
