"""Tests for T24 neural baselines."""
from __future__ import annotations

import numpy as np
import pytest
from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg


def _topic_vecs(n_per_topic: int = 5, n_topics: int = 2, dim: int = 32) -> np.ndarray:
    """Create synthetic embeddings with clear topic clusters."""
    rng = np.random.default_rng(0)
    parts = []
    for t in range(n_topics):
        center = np.zeros(dim)
        center[t * (dim // n_topics):(t + 1) * (dim // n_topics)] = 1.0
        noise = rng.normal(0, 0.05, (n_per_topic, dim))
        vecs = center + noise
        # L2 normalise
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        parts.append(vecs / norms)
    return np.concatenate(parts, axis=0).astype(np.float32)


VECS = _topic_vecs()  # 10 sentences, boundary at 5


def test_cosine_seg_returns_list():
    assert isinstance(cosine_seg(VECS), list)


def test_cosine_seg_boundary_in_range():
    result = cosine_seg(VECS, n_segments=2)
    for b in result:
        assert 1 <= b <= len(VECS) - 1


def test_cosine_seg_n_segments():
    result = cosine_seg(VECS, n_segments=2)
    assert len(result) == 1


def test_cosine_seg_detects_boundary():
    result = cosine_seg(VECS, n_segments=2)
    assert any(3 <= b <= 7 for b in result), f"No boundary near midpoint: {result}"


def test_cosine_seg_short():
    assert cosine_seg(np.eye(2, dtype=np.float32)) == []


def test_cosine_seg_empty():
    assert cosine_seg(np.zeros((0, 4), dtype=np.float32)) == []


def test_cosine_seg_auto_threshold():
    result = cosine_seg(VECS)
    assert isinstance(result, list)
    for b in result:
        assert 1 <= b <= len(VECS) - 1


def test_kmeans_seg_returns_list():
    assert isinstance(kmeans_seg(VECS, n_segments=2), list)


def test_kmeans_seg_detects_boundary():
    result = kmeans_seg(VECS, n_segments=2)
    assert any(3 <= b <= 7 for b in result), f"No boundary near midpoint: {result}"


def test_kmeans_seg_more_segments():
    vecs = _topic_vecs(n_per_topic=5, n_topics=4)
    result = kmeans_seg(vecs, n_segments=4)
    assert len(result) >= 3  # at least 3 transitions for 4 clusters


def test_kmeans_seg_reproducible():
    r1 = kmeans_seg(VECS, n_segments=2, random_state=42)
    r2 = kmeans_seg(VECS, n_segments=2, random_state=42)
    assert r1 == r2


def test_bert_seg_same_as_cosine():
    """bert_seg delegates to cosine_seg — same results expected."""
    r1 = cosine_seg(VECS, window=5, n_segments=2)
    r2 = bert_seg(VECS, window=5, n_segments=2)
    assert r1 == r2
