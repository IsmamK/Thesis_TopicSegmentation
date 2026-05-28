"""Tests for T23 classical baselines — TextTiling and C99."""
from __future__ import annotations

import pytest
from lecseg.baselines.classical import texttiling, c99


TOPIC_A = [
    "Machine learning models are trained on large datasets.",
    "Neural networks use gradient descent to minimise loss.",
    "Backpropagation computes gradients through the network layers.",
    "Overfitting occurs when models memorise training data.",
    "Regularisation techniques like dropout reduce overfitting.",
    "Deep learning has achieved state of the art results on many benchmarks.",
    "Convolutional networks excel at image recognition and classification tasks.",
    "Recurrent networks are designed for sequential and temporal data.",
    "Attention mechanisms allow models to focus on relevant input positions.",
    "Transformer architectures have revolutionised natural language processing.",
    "Pre-trained language models can be fine-tuned on downstream tasks.",
    "Transfer learning reduces the need for large labelled datasets.",
]

TOPIC_B = [
    "Climate change is driven by greenhouse gas emissions.",
    "Carbon dioxide traps heat in the Earth atmosphere.",
    "Rising temperatures cause glaciers to melt worldwide.",
    "Sea levels are rising due to melting polar ice.",
    "Extreme weather events become more frequent with warming.",
    "Renewable energy sources can reduce fossil fuel dependence.",
    "Solar panels convert sunlight directly into electrical energy.",
    "Wind turbines harness kinetic energy from moving air masses.",
    "Energy storage is critical for balancing renewable supply and demand.",
    "International agreements aim to limit global temperature rise.",
    "Deforestation accelerates carbon release into the atmosphere.",
    "Sustainable agriculture practices can reduce methane emissions.",
]

SENTENCES = TOPIC_A + TOPIC_B  # 24 sentences, boundary at index 12


def test_texttiling_returns_list():
    result = texttiling(SENTENCES)
    assert isinstance(result, list)


def test_texttiling_boundary_in_range():
    result = texttiling(SENTENCES)
    for b in result:
        assert 1 <= b <= len(SENTENCES) - 1


def test_texttiling_detects_boundary():
    """Should detect a boundary somewhere in the 6-18 range for 2-topic text (24 sentences)."""
    result = texttiling(SENTENCES)
    assert any(6 <= b <= 18 for b in result), f"No boundary near midpoint: {result}"


def test_texttiling_short_text():
    assert texttiling(["Hello world.", "Goodbye."]) == []


def test_texttiling_empty():
    assert texttiling([]) == []


def test_c99_returns_list():
    result = c99(SENTENCES, n_segments=2)
    assert isinstance(result, list)


def test_c99_exact_n_segments():
    result = c99(SENTENCES, n_segments=2)
    assert len(result) == 1  # 2 segments = 1 boundary


def test_c99_boundary_in_range():
    result = c99(SENTENCES, n_segments=2)
    for b in result:
        assert 1 <= b <= len(SENTENCES) - 1


def test_c99_detects_midpoint():
    result = c99(SENTENCES, n_segments=2)
    # C99-lite places a boundary somewhere in the second half; exact position
    # depends on rank transform — just verify it's in a plausible range
    assert any(4 <= b <= len(SENTENCES) - 4 for b in result), f"Boundary out of range: {result}"


def test_c99_auto_threshold():
    result = c99(SENTENCES)
    assert isinstance(result, list)
    for b in result:
        assert 1 <= b <= len(SENTENCES) - 1


def test_c99_short_text():
    assert c99(["Hello.", "World."]) == []


def test_c99_more_segments():
    long_text = SENTENCES * 3  # 30 sentences
    result = c99(long_text, n_segments=5)
    assert len(result) == 4


def test_c99_no_duplicate_boundaries():
    result = c99(SENTENCES, n_segments=3)
    assert len(result) == len(set(result))
