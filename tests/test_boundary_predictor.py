"""Tests for T26 / N1 two-stage boundary predictor."""
from __future__ import annotations

import numpy as np
import pytest
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor


def _make_vecs(n_per_topic: int = 8, n_topics: int = 2, dim: int = 64) -> np.ndarray:
    """Two-topic synthetic embeddings."""
    rng = np.random.default_rng(42)
    parts = []
    for t in range(n_topics):
        center = np.zeros(dim)
        center[t * (dim // n_topics):(t + 1) * (dim // n_topics)] = 1.0
        noise = rng.normal(0, 0.05, (n_per_topic, dim))
        vecs = center + noise
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        parts.append(vecs / norms)
    return np.concatenate(parts).astype(np.float32)


VECS = _make_vecs()  # 16 sentences, true boundary at 8


def test_predict_returns_list():
    p = TwoStageBoundaryPredictor()
    assert isinstance(p.predict(VECS), list)


def test_predict_n_segments():
    p = TwoStageBoundaryPredictor()
    result = p.predict(VECS, n_segments=2)
    assert len(result) == 1


def test_predict_boundary_in_range():
    p = TwoStageBoundaryPredictor()
    result = p.predict(VECS, n_segments=2)
    for b in result:
        assert 1 <= b <= len(VECS) - 1


def test_predict_detects_midpoint():
    p = TwoStageBoundaryPredictor()
    result = p.predict(VECS, n_segments=2)
    assert any(6 <= b <= 10 for b in result), f"Boundary not near midpoint: {result}"


def test_predict_short_text():
    p = TwoStageBoundaryPredictor()
    assert p.predict(np.eye(2, dtype=np.float32)) == []


def test_predict_with_extra_modality():
    p = TwoStageBoundaryPredictor()
    # Provide visual gap scores that agree with text boundary at index 8
    visual = np.zeros(len(VECS) - 1, dtype=np.float32)
    visual[7] = 1.0  # high score at gap 7 = boundary at sentence 8
    result = p.predict(VECS, modality_scores={"visual": visual}, n_segments=2)
    assert len(result) == 1


def test_predict_hierarchical_returns_tuples():
    p = TwoStageBoundaryPredictor()
    chapters, subtopics = p.predict_hierarchical(VECS, n_chapters=1, n_subtopics=3)
    assert isinstance(chapters, list)
    assert isinstance(subtopics, list)


def test_predict_hierarchical_chapter_subset_of_subtopic():
    p = TwoStageBoundaryPredictor()
    chapters, subtopics = p.predict_hierarchical(VECS, n_chapters=1, n_subtopics=3)
    for b in chapters:
        assert b in subtopics


def test_predict_hierarchical_counts():
    p = TwoStageBoundaryPredictor()
    chapters, subtopics = p.predict_hierarchical(VECS, n_chapters=1, n_subtopics=3)
    assert len(subtopics) == 2  # n_subtopics=3 segments -> 2 boundaries
    assert len(chapters) <= 1


def test_predict_auto_threshold():
    p = TwoStageBoundaryPredictor()
    result = p.predict(VECS)
    assert isinstance(result, list)
    for b in result:
        assert 1 <= b <= len(VECS) - 1
