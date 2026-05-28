"""
T26 / N1 — Two-Stage Boundary Predictor.

Stage 1: Generate candidate boundaries from cosine similarity drops
         (broad, high-recall candidates using a loose threshold).
Stage 2: Re-rank / refine candidates using reliability-weighted fusion
         of multiple modality signals.

This two-stage design reduces false positives compared to single-pass methods
while maintaining high recall from the first stage.

Usage:
    from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor

    predictor = TwoStageBoundaryPredictor(candidate_std=0.5, refine_std=1.2)
    boundaries = predictor.predict(
        text_vecs=text_embeddings,
        modality_scores={"visual": visual_gap_scores},
        n_segments=5,
    )
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Literal

from lecseg.baselines.neural import cosine_seg, _window_vec
from lecseg.models.fusion import ReliabilityWeightedFusion, gap_scores_from_vecs


@dataclass
class TwoStageBoundaryPredictor:
    """
    Two-stage boundary predictor.

    Stage 1: Broad candidate generation (cosine similarity drops, loose threshold).
    Stage 2: Candidate refinement via reliability-weighted fusion.

    Args:
        window:         cosine comparison window size
        candidate_std:  std coefficient for stage-1 threshold (lower = more candidates)
        refine_std:     std coefficient for stage-2 final threshold
        fusion_method:  'entropy' | 'uniform' | 'fixed'
        fixed_weights:  used when fusion_method='fixed'
    """

    window: int = 3
    candidate_std: float = 0.5
    refine_std: float = 1.2
    fusion_method: Literal["entropy", "uniform", "fixed"] = "entropy"
    fixed_weights: dict[str, float] = field(default_factory=dict)

    def _stage1_candidates(
        self,
        text_vecs: np.ndarray,
        n_sentences: int,
    ) -> tuple[list[int], np.ndarray]:
        """
        Stage 1: Find candidate boundaries via cosine similarity drop.

        Returns:
            (candidate_indices, gap_scores)
        """
        gap_scores = gap_scores_from_vecs(text_vecs, window=self.window)

        mean = float(gap_scores.mean())
        std = float(gap_scores.std())
        threshold = mean + self.candidate_std * std

        candidates = [
            i + 1 for i, s in enumerate(gap_scores)
            if s > threshold and 0 < i + 1 < n_sentences
        ]
        return candidates, gap_scores

    def _stage2_refine(
        self,
        candidates: list[int],
        gap_scores: np.ndarray,
        modality_scores: dict[str, np.ndarray],
        n_sentences: int,
        n_segments: int | None,
    ) -> list[int]:
        """
        Stage 2: Refine candidates via fusion, filter by threshold or n_segments.
        """
        all_scores = {"text": gap_scores}
        all_scores.update(modality_scores)

        rwf = ReliabilityWeightedFusion(
            method=self.fusion_method,
            fixed_weights=self.fixed_weights,
        )

        if n_segments is not None:
            return rwf.predict(all_scores, n_sentences, n_segments=n_segments)

        # Filter to candidates only using fused threshold
        fused = rwf.fuse(all_scores)
        mean = float(fused.mean())
        std = float(fused.std())
        threshold = mean + self.refine_std * std

        return sorted(
            i + 1 for i, s in enumerate(fused)
            if s > threshold and (i + 1) in set(candidates)
        )

    def predict(
        self,
        text_vecs: np.ndarray,
        modality_scores: dict[str, np.ndarray] | None = None,
        n_segments: int | None = None,
    ) -> list[int]:
        """
        Run two-stage prediction.

        Args:
            text_vecs:       (N, D) sentence embedding matrix
            modality_scores: additional gap score arrays {name: (N-1,) array}
            n_segments:      target number of segments (None = auto threshold)

        Returns:
            Sorted list of 1-based boundary sentence indices.
        """
        N = len(text_vecs)
        if N < 3:
            return []

        modality_scores = modality_scores or {}
        candidates, gap_scores = self._stage1_candidates(text_vecs, N)

        if not candidates and n_segments is not None:
            # Fall back: treat all positions as candidates
            candidates = list(range(1, N))

        return self._stage2_refine(
            candidates, gap_scores, modality_scores, N, n_segments
        )

    def predict_hierarchical(
        self,
        text_vecs: np.ndarray,
        n_chapters: int,
        n_subtopics: int,
        modality_scores: dict[str, np.ndarray] | None = None,
    ) -> tuple[list[int], list[int]]:
        """
        Predict both chapter-level and subtopic-level boundaries.

        Chapter boundaries are a strict subset of subtopic boundaries.

        Returns:
            (chapter_boundaries, subtopic_boundaries)
        """
        subtopic_bounds = self.predict(
            text_vecs, modality_scores, n_segments=n_subtopics
        )
        # Chapter boundaries are top-n_chapters by gap score from subtopic candidates
        if not subtopic_bounds:
            return [], []

        gap_scores = gap_scores_from_vecs(text_vecs, window=self.window)
        subtopic_scores = [(b, float(gap_scores[b - 1])) for b in subtopic_bounds
                           if 0 < b <= len(gap_scores)]
        subtopic_scores.sort(key=lambda x: -x[1])
        n_chapter_boundaries = max(0, n_chapters - 1)
        chapter_bounds = sorted(b for b, _ in subtopic_scores[:n_chapter_boundaries])

        return chapter_bounds, subtopic_bounds
