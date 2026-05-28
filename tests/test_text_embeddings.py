"""Tests for T19 text embeddings."""
from __future__ import annotations

import json
import numpy as np
import pytest
from lecseg.features.text_embeddings import embed_sentences, embed_file


SENTS = [
    "Machine learning models learn from data.",
    "Neural networks are a type of machine learning model.",
    "Climate change affects the global temperature.",
]


def test_embed_returns_ndarray():
    vecs = embed_sentences(SENTS, model="sbert")
    assert isinstance(vecs, np.ndarray)


def test_embed_shape():
    vecs = embed_sentences(SENTS, model="sbert")
    assert vecs.shape[0] == len(SENTS)
    assert vecs.shape[1] > 0


def test_embed_dtype():
    vecs = embed_sentences(SENTS, model="sbert")
    assert vecs.dtype == np.float32


def test_embed_normalised():
    vecs = embed_sentences(SENTS, model="sbert", normalize=True)
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_embed_prefix():
    # Passing a prefix should still return correct shape
    vecs = embed_sentences(SENTS[:1], model="sbert", prefix="passage: ")
    assert vecs.shape[0] == 1
    assert vecs.shape[1] == 384


def test_embed_empty():
    vecs = embed_sentences([], model="sbert")
    assert vecs.shape[0] == 0


def test_similar_sentences_closer():
    """ML sentences should be closer to each other than to climate sentence."""
    vecs = embed_sentences(SENTS, model="sbert")
    sim_ml = float(vecs[0] @ vecs[1])
    sim_cross = float(vecs[0] @ vecs[2])
    assert sim_ml > sim_cross


def test_embed_file(tmp_path):
    data = {
        "video_id": "test",
        "sentences": [{"idx": i, "start": float(i), "end": float(i+1), "text": s}
                      for i, s in enumerate(SENTS)]
    }
    sfile = tmp_path / "sentences.json"
    sfile.write_text(json.dumps(data), encoding="utf-8")

    vecs = embed_file(sfile, model="sbert")
    assert vecs.shape == (len(SENTS), 384)  # MiniLM is 384-dim


def test_embed_file_saves_npy(tmp_path):
    data = {
        "video_id": "test",
        "sentences": [{"idx": 0, "start": 0.0, "end": 1.0, "text": "Hello world."}]
    }
    sfile = tmp_path / "sentences.json"
    sfile.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "embeddings.npy"

    embed_file(sfile, out_path=out, model="sbert")
    assert out.exists()
    loaded = np.load(str(out))
    assert loaded.shape[0] == 1
