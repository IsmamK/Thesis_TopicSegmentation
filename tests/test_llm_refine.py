"""Tests for T28 / N4 LLM boundary refinement and titling.

These tests mock Ollama so they run without a live Ollama instance.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from lecseg.refine.llm_refine import LLMRefiner


SENTS = [
    "Machine learning models are trained on data.",
    "Neural networks use backpropagation for training.",
    "Gradient descent minimises the loss function.",
    "Climate change is driven by CO2 emissions.",
    "Rising temperatures affect global ecosystems.",
    "Sea levels are rising due to melting ice.",
]


def _mock_generate(response: str):
    """Patch _ollama_generate to return a fixed response."""
    return patch("lecseg.refine.llm_refine._ollama_generate", return_value=response)


def test_title_segment_returns_string():
    with _mock_generate("Introduction to Machine Learning"):
        refiner = LLMRefiner()
        title = refiner.title_segment(SENTS[:3])
    assert isinstance(title, str)
    assert len(title) > 0


def test_title_segment_strips_quotes():
    with _mock_generate('"Introduction to ML"'):
        refiner = LLMRefiner()
        title = refiner.title_segment(SENTS[:3])
    assert '"' not in title


def test_title_segments_count():
    with _mock_generate("Some Title"):
        refiner = LLMRefiner()
        titles = refiner.title_segments(SENTS, boundaries=[3])
    assert len(titles) == 2  # 1 boundary = 2 segments


def test_title_segments_no_boundaries():
    with _mock_generate("Overview of the Lecture"):
        refiner = LLMRefiner()
        titles = refiner.title_segments(SENTS, boundaries=[])
    assert len(titles) == 1


def test_refine_boundary_valid_response():
    with _mock_generate("3"):
        refiner = LLMRefiner()
        result = refiner.refine_boundary(SENTS, boundary=3, tolerance=2)
    assert 1 <= result <= len(SENTS) - 1


def test_refine_boundary_out_of_range_defaults_to_original():
    with _mock_generate("99"):  # out of tolerance
        refiner = LLMRefiner()
        result = refiner.refine_boundary(SENTS, boundary=3, tolerance=1)
    assert result == 3  # falls back to original


def test_refine_boundaries_no_duplicates():
    # Both boundaries get refined to same position
    with _mock_generate("3"):
        refiner = LLMRefiner()
        with patch.object(refiner, "_is_available", return_value=True):
            result = refiner.refine_boundaries(SENTS, boundaries=[3, 4], tolerance=2)
    assert len(result) == len(set(result))


def test_refine_boundaries_fallback_when_unavailable():
    refiner = LLMRefiner()
    with patch.object(refiner, "_is_available", return_value=False):
        result = refiner.refine_boundaries(SENTS, boundaries=[3, 4])
    assert result == [3, 4]  # unchanged


def test_refine_boundaries_sorted():
    with _mock_generate("3"):
        refiner = LLMRefiner()
        with patch.object(refiner, "_is_available", return_value=True):
            result = refiner.refine_boundaries(SENTS, [2, 4], tolerance=1)
    assert result == sorted(result)
