"""Sentence chunking for improved embedding quality.

Averages adjacent sentence embeddings into chunks of `chunk_size`. Working
at the chunk level reduces noise from one-sentence asides and gives the
segmenter a cleaner topic-coherence signal (TreeSeg-style).
"""
from __future__ import annotations

import math
import numpy as np


def chunk_vecs(vecs: np.ndarray, chunk_size: int = 4) -> np.ndarray:
    """Average embeddings into non-overlapping chunks of chunk_size.

    Returns array of shape (ceil(N/chunk_size), D).
    """
    if chunk_size <= 1:
        return vecs.astype(np.float32, copy=False)
    N = len(vecs)
    if N == 0:
        return vecs.astype(np.float32, copy=False)
    n_chunks = math.ceil(N / chunk_size)
    D = vecs.shape[1]
    out = np.zeros((n_chunks, D), dtype=np.float32)
    for i in range(n_chunks):
        lo = i * chunk_size
        hi = min(lo + chunk_size, N)
        out[i] = vecs[lo:hi].mean(axis=0)
    return out


def chunk_to_sentence_boundary(chunk_boundary: int, chunk_size: int, n_sentences: int) -> int:
    """Convert a chunk-level boundary index to a sentence index.

    A chunk boundary `i` separates chunk i-1 and chunk i, which maps to
    the sentence at position i * chunk_size.
    """
    return max(1, min(int(chunk_boundary) * int(chunk_size), n_sentences - 1))


def chunk_boundaries_to_sentences(
    chunk_boundaries: list[int],
    chunk_size: int,
    n_sentences: int,
) -> list[int]:
    """Convert a list of chunk-level boundaries to sentence-index boundaries."""
    out = []
    for b in chunk_boundaries:
        s = chunk_to_sentence_boundary(b, chunk_size, n_sentences)
        if 0 < s < n_sentences:
            out.append(s)
    return sorted(set(out))
