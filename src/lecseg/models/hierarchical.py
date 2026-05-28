"""
T27 / N3 — Hierarchical segmentation output.

Takes flat boundary predictions and produces a two-level hierarchy:
    - Chapter level:   coarse segmentation (major topic shifts)
    - Subtopic level:  fine segmentation within chapters

The hierarchy is enforced by ensuring every chapter boundary is also
a subtopic boundary (chapters are a strict subset of subtopics).

Usage:
    from lecseg.models.hierarchical import HierarchicalSegmenter, SegmentTree

    seg = HierarchicalSegmenter()
    result = seg.segment(
        text_vecs=vecs,
        n_chapters=5,
        n_subtopics=15,
    )
    print(result.chapters)   # [20, 45, 80, 110, 150]
    print(result.subtopics)  # denser list including chapter boundaries
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.fusion import ReliabilityWeightedFusion, gap_scores_from_vecs


@dataclass
class SegmentTree:
    """Hierarchical segmentation result."""

    n_sentences: int
    chapters: list[int]      # 1-based boundary indices (chapter level)
    subtopics: list[int]     # 1-based boundary indices (subtopic level)

    def chapter_spans(self) -> list[tuple[int, int]]:
        """Return (start, end) inclusive sentence index spans for each chapter."""
        bounds = [0] + self.chapters + [self.n_sentences]
        return [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)]

    def subtopic_spans(self) -> list[tuple[int, int]]:
        """Return (start, end) inclusive sentence index spans for each subtopic."""
        bounds = [0] + self.subtopics + [self.n_sentences]
        return [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)]

    def subtopics_within_chapter(self, chapter_idx: int) -> list[tuple[int, int]]:
        """Return subtopic spans that fall within a given chapter."""
        ch_start, ch_end = self.chapter_spans()[chapter_idx]
        return [
            span for span in self.subtopic_spans()
            if ch_start <= span[0] and span[1] <= ch_end
        ]

    def n_chapters(self) -> int:
        return len(self.chapters) + 1

    def n_subtopics(self) -> int:
        return len(self.subtopics) + 1

    def as_dict(self) -> dict:
        return {
            "n_sentences": self.n_sentences,
            "chapters": self.chapters,
            "subtopics": self.subtopics,
            "n_chapters": self.n_chapters(),
            "n_subtopics": self.n_subtopics(),
        }

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "SegmentTree":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            n_sentences=d["n_sentences"],
            chapters=d["chapters"],
            subtopics=d["subtopics"],
        )


class HierarchicalSegmenter:
    """
    Produces a two-level (chapter + subtopic) segmentation hierarchy.

    Args:
        predictor:      underlying boundary predictor (default: TwoStageBoundaryPredictor)
        chapter_ratio:  if n_chapters not given, use this fraction of n_subtopics
    """

    def __init__(
        self,
        predictor: TwoStageBoundaryPredictor | None = None,
        chapter_ratio: float = 0.3,
    ):
        self.predictor = predictor or TwoStageBoundaryPredictor()
        self.chapter_ratio = chapter_ratio

    def segment(
        self,
        text_vecs: np.ndarray,
        n_subtopics: int,
        n_chapters: int | None = None,
        modality_scores: dict[str, np.ndarray] | None = None,
    ) -> SegmentTree:
        """
        Produce hierarchical segmentation.

        Args:
            text_vecs:       (N, D) sentence embedding matrix
            n_subtopics:     target number of subtopic segments
            n_chapters:      target number of chapter segments (None = auto)
            modality_scores: additional gap score arrays

        Returns:
            SegmentTree with chapter and subtopic boundaries.
        """
        N = len(text_vecs)
        if n_chapters is None:
            n_chapters = max(2, int(round(n_subtopics * self.chapter_ratio)))

        n_chapters = min(n_chapters, n_subtopics)

        chapters, subtopics = self.predictor.predict_hierarchical(
            text_vecs,
            n_chapters=n_chapters,
            n_subtopics=n_subtopics,
            modality_scores=modality_scores,
        )

        # Ensure all chapter boundaries are in subtopics
        subtopic_set = set(subtopics)
        for b in chapters:
            subtopic_set.add(b)
        subtopics = sorted(subtopic_set)

        return SegmentTree(
            n_sentences=N,
            chapters=sorted(chapters),
            subtopics=subtopics,
        )

    def segment_auto(
        self,
        text_vecs: np.ndarray,
        modality_scores: dict[str, np.ndarray] | None = None,
    ) -> SegmentTree:
        """
        Auto-detect number of segments using gap score distribution.
        Estimates n_subtopics from the number of significant peaks.
        """
        N = len(text_vecs)
        gap_scores = gap_scores_from_vecs(text_vecs, window=self.predictor.window)

        # Count peaks above mean + 0.5*std as initial n_subtopics estimate
        mean = float(gap_scores.mean())
        std = float(gap_scores.std())
        n_subtopics = max(2, sum(1 for s in gap_scores if s > mean + 0.5 * std) + 1)
        n_subtopics = min(n_subtopics, N // 3)  # cap at N/3

        return self.segment(text_vecs, n_subtopics=n_subtopics,
                            modality_scores=modality_scores)
