"""Tests for T21 modality alignment."""
from __future__ import annotations

import numpy as np
import pytest
from lecseg.features.alignment import FeatureMatrix, assign_to_sentences, align_to_sentences


SENTS = [
    {"idx": 0, "start": 0.0,  "end": 5.0,  "text": "First sentence."},
    {"idx": 1, "start": 5.0,  "end": 10.0, "text": "Second sentence."},
    {"idx": 2, "start": 10.0, "end": 15.0, "text": "Third sentence."},
]


def test_feature_matrix_add():
    fm = FeatureMatrix(n_sentences=3)
    arr = np.ones((3, 4), dtype=np.float32)
    fm.add("text", arr)
    assert "text" in fm.modalities


def test_feature_matrix_wrong_shape():
    fm = FeatureMatrix(n_sentences=3)
    with pytest.raises(ValueError):
        fm.add("bad", np.ones((5, 4)))


def test_feature_matrix_concat():
    fm = FeatureMatrix(n_sentences=3)
    fm.add("a", np.ones((3, 2)))
    fm.add("b", np.ones((3, 3)))
    X = fm.concat()
    assert X.shape == (3, 5)


def test_feature_matrix_concat_selected():
    fm = FeatureMatrix(n_sentences=3)
    fm.add("a", np.ones((3, 2)))
    fm.add("b", np.ones((3, 3)))
    X = fm.concat(names=["a"])
    assert X.shape == (3, 2)


def test_feature_matrix_dims():
    fm = FeatureMatrix(n_sentences=3)
    fm.add("text", np.ones((3, 768)))
    assert fm.dims() == {"text": 768}


def test_feature_matrix_save_load(tmp_path):
    fm = FeatureMatrix(n_sentences=3)
    fm.add("text", np.eye(3, dtype=np.float32))
    fm.save(tmp_path)
    loaded = FeatureMatrix.load(tmp_path)
    assert "text" in loaded.modalities
    np.testing.assert_array_equal(loaded.modalities["text"], fm.modalities["text"])


def test_assign_to_sentences_basic():
    sent_times = [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0)]
    feat_times = [(1.0, 2.0), (6.0, 7.0), (11.0, 12.0)]
    feat_vecs = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    out = assign_to_sentences(sent_times, feat_times, feat_vecs)
    assert out.shape == (3, 2)
    np.testing.assert_array_almost_equal(out[0], [1.0, 0.0])
    np.testing.assert_array_almost_equal(out[1], [0.0, 1.0])
    np.testing.assert_array_almost_equal(out[2], [1.0, 1.0])


def test_assign_multiple_per_sentence():
    sent_times = [(0.0, 10.0), (10.0, 20.0)]
    feat_times = [(1.0, 2.0), (3.0, 4.0), (11.0, 12.0)]
    feat_vecs = np.array([[2.0], [4.0], [1.0]], dtype=np.float32)
    out = assign_to_sentences(sent_times, feat_times, feat_vecs, agg="mean")
    assert out[0, 0] == pytest.approx(3.0)  # mean(2, 4)
    assert out[1, 0] == pytest.approx(1.0)


def test_align_to_sentences():
    text_vecs = np.eye(3, dtype=np.float32)
    fm = align_to_sentences(SENTS, text_vecs=text_vecs)
    assert fm.n_sentences == 3
    assert "text" in fm.modalities
    assert fm.modalities["text"].shape == (3, 3)


def test_align_no_text():
    fm = align_to_sentences(SENTS)
    assert fm.n_sentences == 3
    assert len(fm.modalities) == 0


def test_align_extra_modality():
    feat_times = [(2.5, 3.5), (7.5, 8.5), (12.5, 13.5)]
    feat_vecs = np.ones((3, 2), dtype=np.float32)
    fm = align_to_sentences(
        SENTS,
        extra_modalities={"visual": (feat_times, feat_vecs)},
    )
    assert "visual" in fm.modalities
    assert fm.modalities["visual"].shape == (3, 2)


def test_concat_empty():
    fm = FeatureMatrix(n_sentences=0)
    X = fm.concat()
    assert X.shape[0] == 0
