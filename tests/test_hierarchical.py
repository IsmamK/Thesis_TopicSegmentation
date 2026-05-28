"""Tests for T27 / N3 hierarchical segmentation."""
from __future__ import annotations

import json
import numpy as np
import pytest
from lecseg.models.hierarchical import HierarchicalSegmenter, SegmentTree


def _make_vecs(n_per_topic: int = 6, n_topics: int = 3, dim: int = 48) -> np.ndarray:
    rng = np.random.default_rng(7)
    parts = []
    for t in range(n_topics):
        center = np.zeros(dim)
        center[t * (dim // n_topics):(t + 1) * (dim // n_topics)] = 1.0
        noise = rng.normal(0, 0.05, (n_per_topic, dim))
        vecs = center + noise
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        parts.append(vecs / norms)
    return np.concatenate(parts).astype(np.float32)


VECS = _make_vecs()  # 18 sentences, true boundaries at 6, 12


def test_segment_returns_tree():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3)
    assert isinstance(result, SegmentTree)


def test_segment_counts():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3, n_chapters=2)
    assert result.n_subtopics() == 3
    assert result.n_chapters() == 2


def test_chapters_subset_of_subtopics():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3, n_chapters=2)
    subtopic_set = set(result.subtopics)
    for b in result.chapters:
        assert b in subtopic_set


def test_chapter_spans_cover_all():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3, n_chapters=2)
    spans = result.chapter_spans()
    assert spans[0][0] == 0
    assert spans[-1][1] == len(VECS) - 1


def test_subtopic_spans_cover_all():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3, n_chapters=2)
    spans = result.subtopic_spans()
    assert spans[0][0] == 0
    assert spans[-1][1] == len(VECS) - 1


def test_subtopics_within_chapter():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=6, n_chapters=2)
    for i in range(result.n_chapters()):
        inner = result.subtopics_within_chapter(i)
        assert len(inner) >= 1


def test_as_dict():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3)
    d = result.as_dict()
    assert "chapters" in d
    assert "subtopics" in d
    assert d["n_chapters"] == result.n_chapters()


def test_save_load(tmp_path):
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3, n_chapters=2)
    p = tmp_path / "seg.json"
    result.save(p)
    loaded = SegmentTree.load(p)
    assert loaded.chapters == result.chapters
    assert loaded.subtopics == result.subtopics
    assert loaded.n_sentences == result.n_sentences


def test_segment_auto():
    seg = HierarchicalSegmenter()
    result = seg.segment_auto(VECS)
    assert result.n_chapters() >= 2
    assert result.n_subtopics() >= 2


def test_boundary_indices_in_range():
    seg = HierarchicalSegmenter()
    result = seg.segment(VECS, n_subtopics=3)
    for b in result.chapters + result.subtopics:
        assert 1 <= b <= len(VECS) - 1
