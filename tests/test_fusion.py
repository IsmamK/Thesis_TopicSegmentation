"""Tests for T25 / N2 reliability-weighted fusion."""
from __future__ import annotations

import numpy as np
import pytest
from lecseg.models.fusion import ReliabilityWeightedFusion, gap_scores_from_vecs, _entropy


def test_entropy_uniform():
    # Uniform distribution -> max entropy (1.0)
    scores = np.ones(10, dtype=np.float32)
    assert _entropy(scores) == pytest.approx(1.0, abs=0.01)


def test_entropy_deterministic():
    # All-zero except one peak -> low entropy
    scores = np.zeros(10, dtype=np.float32)
    scores[5] = 1.0
    assert _entropy(scores) < 0.3


def test_fuse_single_modality():
    rwf = ReliabilityWeightedFusion()
    s = np.array([0.1, 0.9, 0.2, 0.8, 0.1], dtype=np.float32)
    fused = rwf.fuse({"text": s})
    assert fused.shape == s.shape
    # Single modality: should be normalised version of s
    assert fused.max() == pytest.approx(1.0, abs=1e-5)
    assert fused.min() == pytest.approx(0.0, abs=1e-5)


def test_fuse_two_modalities_shape():
    rwf = ReliabilityWeightedFusion()
    s1 = np.array([0.1, 0.8, 0.2], dtype=np.float32)
    s2 = np.array([0.2, 0.7, 0.3], dtype=np.float32)
    fused = rwf.fuse({"text": s1, "visual": s2})
    assert fused.shape == (3,)


def test_fuse_length_mismatch():
    rwf = ReliabilityWeightedFusion()
    with pytest.raises(ValueError):
        rwf.fuse({"a": np.ones(3), "b": np.ones(5)})


def test_fuse_empty():
    rwf = ReliabilityWeightedFusion()
    with pytest.raises(ValueError):
        rwf.fuse({})


def test_uniform_weights():
    rwf = ReliabilityWeightedFusion(method="uniform")
    s1 = np.array([1.0, 0.0, 0.5], dtype=np.float32)
    s2 = np.array([0.0, 1.0, 0.5], dtype=np.float32)
    weights = rwf.compute_weights({"a": s1, "b": s2})
    assert weights["a"] == pytest.approx(0.5)
    assert weights["b"] == pytest.approx(0.5)


def test_fixed_weights():
    rwf = ReliabilityWeightedFusion(method="fixed", fixed_weights={"text": 2.0, "visual": 1.0})
    s = np.ones(3, dtype=np.float32)
    weights = rwf.compute_weights({"text": s, "visual": s})
    assert weights["text"] == pytest.approx(2 / 3, abs=1e-5)
    assert weights["visual"] == pytest.approx(1 / 3, abs=1e-5)


def test_entropy_method_high_confidence_gets_more_weight():
    rwf = ReliabilityWeightedFusion(method="entropy")
    # text has clear peak (high confidence), visual is uniform (low confidence)
    text_scores = np.zeros(9, dtype=np.float32)
    text_scores[4] = 1.0  # sharp peak -> low entropy -> high reliability
    visual_scores = np.ones(9, dtype=np.float32) * 0.5  # uniform -> high entropy -> low reliability
    weights = rwf.compute_weights({"text": text_scores, "visual": visual_scores})
    assert weights["text"] > weights["visual"]


def test_predict_n_segments():
    rwf = ReliabilityWeightedFusion()
    scores = {"text": np.array([0.1, 0.8, 0.2, 0.9, 0.1, 0.3], dtype=np.float32)}
    boundaries = rwf.predict(scores, n_sentences=7, n_segments=3)
    assert len(boundaries) == 2


def test_predict_boundaries_in_range():
    rwf = ReliabilityWeightedFusion()
    scores = {"text": np.array([0.1, 0.8, 0.2, 0.9, 0.1], dtype=np.float32)}
    boundaries = rwf.predict(scores, n_sentences=6, n_segments=2)
    for b in boundaries:
        assert 1 <= b <= 5


def test_reliability_report():
    rwf = ReliabilityWeightedFusion()
    s = np.array([0.1, 0.8, 0.2], dtype=np.float32)
    report = rwf.reliability_report({"text": s})
    assert "text" in report
    assert "entropy" in report["text"]
    assert "effective_weight" in report["text"]


def test_gap_scores_from_vecs_shape():
    rng = np.random.default_rng(0)
    vecs = rng.normal(0, 1, (10, 64)).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs /= norms
    scores = gap_scores_from_vecs(vecs)
    assert scores.shape == (9,)


def test_gap_scores_from_vecs_range():
    rng = np.random.default_rng(1)
    vecs = rng.normal(0, 1, (10, 64)).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs /= norms
    scores = gap_scores_from_vecs(vecs)
    assert (scores >= 0).all()
    assert (scores <= 2).all()  # cosine dissimilarity in [0, 2]


def test_gap_scores_detects_topic_shift():
    """Boundary between two distinct topic clusters should have high gap score."""
    rng = np.random.default_rng(2)
    # 5 sentences on topic A, 5 on topic B
    topic_a = np.zeros((5, 32), dtype=np.float32)
    topic_a[:, :16] = 1.0 + rng.normal(0, 0.1, (5, 16)).astype(np.float32)
    topic_b = np.zeros((5, 32), dtype=np.float32)
    topic_b[:, 16:] = 1.0 + rng.normal(0, 0.1, (5, 16)).astype(np.float32)
    vecs = np.concatenate([topic_a, topic_b])
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / np.maximum(norms, 1e-8)
    scores = gap_scores_from_vecs(vecs, window=2)
    # The gap at index 4 (between sentence 4 and 5) should be highest
    assert scores[4] == scores.max()
