"""Tests for T20 visual embeddings — runs without CLIP installed."""
from __future__ import annotations

import numpy as np
import pytest
from lecseg.features.visual_embeddings import embed_keyframes, CLIP_DIM


def test_embed_empty():
    vecs = embed_keyframes([])
    assert vecs.shape == (0, CLIP_DIM)


def test_embed_returns_ndarray():
    """With CLIP unavailable, returns zero vectors."""
    # Create minimal fake PIL images
    try:
        from PIL import Image
        frames = [Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)) for _ in range(3)]
    except ImportError:
        pytest.skip("PIL not available")

    vecs = embed_keyframes(frames)
    assert isinstance(vecs, np.ndarray)
    assert vecs.shape[0] == 3
    assert vecs.shape[1] == CLIP_DIM
    assert vecs.dtype == np.float32


def test_embed_shape_consistent():
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL not available")

    rng = np.random.default_rng(0)
    frames = [Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8))
              for _ in range(5)]
    vecs = embed_keyframes(frames)
    assert vecs.shape == (5, CLIP_DIM)
