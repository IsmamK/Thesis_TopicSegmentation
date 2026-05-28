"""
T21 — Align all modalities to the sentence timeline.

Given sentence records (from T15) with start/end timestamps, this module
provides utilities to align any time-indexed feature (visual keyframes,
prosody segments, slide OCR regions) to the nearest sentence index.

The output is a FeatureMatrix: a dict of {modality: np.ndarray} where each
array has shape (N_sentences, D_modality) and is ready for downstream fusion.

Usage:
    from lecseg.features.alignment import FeatureMatrix, align_to_sentences

    fm = align_to_sentences(
        sentences=sents,           # list of {idx, start, end, text}
        text_vecs=text_embeddings, # (N, D) from T19
    )
    X = fm.concat()                # (N, D_total) concatenated feature matrix
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass
class FeatureMatrix:
    """Container for per-sentence aligned feature arrays."""

    n_sentences: int
    modalities: dict[str, np.ndarray] = field(default_factory=dict)

    def add(self, name: str, array: np.ndarray) -> None:
        """Register a (N_sentences, D) array under `name`."""
        if array.shape[0] != self.n_sentences:
            raise ValueError(
                f"Array '{name}' has {array.shape[0]} rows but expected {self.n_sentences}"
            )
        self.modalities[name] = array.astype(np.float32)

    def concat(self, names: list[str] | None = None) -> np.ndarray:
        """
        Concatenate selected (or all) modalities column-wise.
        Returns (N_sentences, D_total) float32 array.
        """
        if self.n_sentences == 0:
            return np.zeros((0, 0), dtype=np.float32)
        keys = names if names is not None else list(self.modalities.keys())
        arrays = [self.modalities[k] for k in keys if k in self.modalities]
        if not arrays:
            return np.zeros((self.n_sentences, 0), dtype=np.float32)
        return np.concatenate(arrays, axis=1)

    def dims(self) -> dict[str, int]:
        """Return {modality: feature_dim} mapping."""
        return {k: v.shape[1] if v.ndim > 1 else 1 for k, v in self.modalities.items()}

    def save(self, out_dir: Path | str) -> None:
        """Save each modality array as <out_dir>/<name>.npy."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, arr in self.modalities.items():
            np.save(str(out_dir / f"{name}.npy"), arr)

    @classmethod
    def load(cls, out_dir: Path | str) -> "FeatureMatrix":
        """Load all .npy files from a directory saved by save()."""
        out_dir = Path(out_dir)
        modalities = {}
        for npy in sorted(out_dir.glob("*.npy")):
            modalities[npy.stem] = np.load(str(npy))
        n = next(iter(modalities.values())).shape[0] if modalities else 0
        fm = cls(n_sentences=n)
        fm.modalities = modalities
        return fm


def _midpoint(start: float, end: float) -> float:
    return (start + end) / 2


def assign_to_sentences(
    sent_times: list[tuple[float, float]],
    feature_times: list[tuple[float, float]],
    feature_vecs: np.ndarray,
    agg: str = "mean",
) -> np.ndarray:
    """
    Assign each feature vector to the sentence whose interval contains its midpoint,
    then aggregate (mean/max) multiple features per sentence.

    Args:
        sent_times:    list of (start, end) for each sentence
        feature_times: list of (start, end) for each feature frame
        feature_vecs:  (N_features, D) array
        agg:           'mean' or 'max' aggregation

    Returns:
        (N_sentences, D) float32 array (zero-vector for sentences with no features)
    """
    n_sents = len(sent_times)
    D = feature_vecs.shape[1] if feature_vecs.ndim > 1 else 1
    out = np.zeros((n_sents, D), dtype=np.float32)
    counts = np.zeros(n_sents, dtype=np.int32)

    for fi, (fs, fe) in enumerate(feature_times):
        mid = _midpoint(fs, fe)
        # Find sentence that contains this midpoint
        assigned = -1
        for si, (ss, se) in enumerate(sent_times):
            if ss <= mid < se:
                assigned = si
                break
        if assigned == -1:
            # Fall back: nearest sentence by midpoint distance
            sent_mids = [_midpoint(s, e) for s, e in sent_times]
            assigned = int(np.argmin([abs(m - mid) for m in sent_mids]))

        vec = feature_vecs[fi].astype(np.float32).reshape(-1)[:D]
        if agg == "max":
            out[assigned] = np.maximum(out[assigned], vec)
        else:  # mean
            out[assigned] += vec
            counts[assigned] += 1

    if agg == "mean":
        nonzero = counts > 0
        out[nonzero] /= counts[nonzero, np.newaxis]

    return out


def align_to_sentences(
    sentences: list[dict],
    text_vecs: np.ndarray | None = None,
    extra_modalities: dict[str, tuple[list[tuple[float, float]], np.ndarray]] | None = None,
) -> FeatureMatrix:
    """
    Build a FeatureMatrix from sentence records and optional modality arrays.

    Args:
        sentences:        list of {idx, start, end, text} dicts
        text_vecs:        (N, D) text embeddings in sentence order (already aligned)
        extra_modalities: dict of {name: (feature_times, feature_vecs)} for
                          modalities that need temporal alignment (visual, prosody)

    Returns:
        FeatureMatrix with all aligned modalities
    """
    n = len(sentences)
    fm = FeatureMatrix(n_sentences=n)

    if text_vecs is not None:
        fm.add("text", text_vecs)

    if extra_modalities:
        sent_times = [(s["start"], s["end"]) for s in sentences]
        for name, (feat_times, feat_vecs) in extra_modalities.items():
            aligned = assign_to_sentences(sent_times, feat_times, feat_vecs)
            fm.add(name, aligned)

    return fm


def load_and_align(
    sentences_json: Path | str,
    embeddings_npy: Path | str | None = None,
    model: str = "mpnet",
) -> FeatureMatrix:
    """
    Load sentences.json and optional pre-computed embeddings.npy, return FeatureMatrix.
    If embeddings_npy is None, computes embeddings on-the-fly.
    """
    sentences_json = Path(sentences_json)
    data = json.loads(sentences_json.read_text(encoding="utf-8"))
    sentences = data.get("sentences", [])

    if embeddings_npy is not None and Path(embeddings_npy).exists():
        text_vecs = np.load(str(embeddings_npy)).astype(np.float32)
    else:
        from lecseg.features.text_embeddings import embed_sentences
        texts = [s["text"] for s in sentences]
        text_vecs = embed_sentences(texts, model=model) if texts else None

    return align_to_sentences(sentences, text_vecs=text_vecs)
