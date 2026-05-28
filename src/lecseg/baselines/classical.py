"""
T23 — Classical text segmentation baselines.

Baselines:
    TextTiling  — NLTK reference implementation of Hearst 1994.
                  Validated on Choi benchmark: Pk≈0.49 (published ≈0.46).
    C99         — Simplified reimplementation of Choi 2000.
                  NOTE: this is a lite reimplementation (Pk≈0.51 on Choi vs
                  published ≈0.12). Referred to as "C99-lite" in the thesis.

Both take a list of sentence strings and return a list of boundary indices
(sentence positions where a new segment starts, 1-indexed from 1 to N-1).

Usage:
    from lecseg.baselines.classical import texttiling, c99

    boundaries = texttiling(sentences)
    boundaries = c99(sentences, n_segments=5)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stripping punctuation."""
    return re.findall(r"[a-z']+", text.lower())


def _tf(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a if t in b)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


# ---------------------------------------------------------------------------
# TextTiling
# ---------------------------------------------------------------------------

def texttiling(
    sentences: Sequence[str],
    w: int = 20,
    k: int = 10,
    smoothing_passes: int = 1,
) -> list[int]:
    """
    TextTiling (Hearst 1994) via NLTK's reference implementation.

    Validated on Choi (2000) benchmark: Pk=0.49 (published=0.46).

    Args:
        sentences:        list of sentence strings
        w:                pseudo-sentence block size in tokens (default 20)
        k:                comparison window in pseudo-sentences (default 10)
        smoothing_passes: ignored (NLTK handles smoothing internally)

    Returns:
        List of 1-based sentence boundary indices.
    """
    n = len(sentences)
    if n < 3:
        return []

    try:
        from nltk.tokenize import TextTilingTokenizer
        text = "\n\n".join(sentences)
        ttt = TextTilingTokenizer(w=w, k=k)
        tiles = ttt.tokenize(text)
        boundaries: list[int] = []
        pos = 0
        for tile in tiles[:-1]:
            tile_sents = [s.strip() for s in tile.split("\n\n") if s.strip()]
            pos += len(tile_sents)
            if 0 < pos < n:
                boundaries.append(pos)
        return sorted(set(boundaries))
    except Exception:
        return _texttiling_fallback(sentences, w, k, smoothing_passes)


def _texttiling_fallback(
    sentences: Sequence[str],
    w: int = 20,
    k: int = 10,
    smoothing_passes: int = 1,
) -> list[int]:
    """Custom TextTiling fallback if NLTK is unavailable."""
    n = len(sentences)
    tokens: list[str] = []
    sent_ends: list[int] = []
    for s in sentences:
        tokens.extend(_tokenize(s))
        sent_ends.append(len(tokens))

    T = len(tokens)
    if T == 0:
        return []

    w = min(w, max(3, T // 10))
    n_blocks = max(1, T // w)
    k = min(k, max(2, n_blocks // 3))
    blocks: list[Counter] = []
    for i in range(n_blocks):
        start = i * w
        end = start + w if i < n_blocks - 1 else T
        blocks.append(_tf(tokens[start:end]))

    gaps = []
    for i in range(1, n_blocks):
        left_start = max(0, i - k)
        right_end = min(n_blocks, i + k)
        left = sum((blocks[j] for j in range(left_start, i)), Counter())
        right = sum((blocks[j] for j in range(i, right_end)), Counter())
        gaps.append(_cosine(left, right))

    if not gaps:
        return []

    depth = []
    for i, g in enumerate(gaps):
        left_max = max(gaps[:i + 1])
        right_max = max(gaps[i:])
        depth.append((left_max - g) + (right_max - g))

    for _ in range(smoothing_passes):
        smoothed = depth[:]
        for i in range(1, len(depth) - 1):
            smoothed[i] = (depth[i - 1] + depth[i] + depth[i + 1]) / 3
        depth = smoothed

    boundary_block_positions: list[int] = []
    for i in range(1, len(depth) - 1):
        if depth[i] >= depth[i - 1] and depth[i] > depth[i + 1] and depth[i] > 0:
            boundary_block_positions.append(i)

    block_token_ends = [min((j + 1) * w, T) for j in range(n_blocks)]
    boundaries: set[int] = set()
    for bp in boundary_block_positions:
        token_pos = block_token_ends[bp]
        for si, se in enumerate(sent_ends):
            if se >= token_pos:
                if 0 < si < n:
                    boundaries.add(si)
                break

    return sorted(boundaries)


# ---------------------------------------------------------------------------
# C99
# ---------------------------------------------------------------------------

def c99(
    sentences: Sequence[str],
    n_segments: int | None = None,
    std_coeff: float = 1.2,
    window: int = 5,
) -> list[int]:
    """
    C99 (Choi 2000) — rank-transformed cosine similarity matrix segmentation.

    Args:
        sentences:   list of sentence strings
        n_segments:  desired number of segments (None = automatic threshold)
        std_coeff:   boundary threshold = mean + std_coeff * std (auto mode)
        window:      local rank normalisation window radius

    Returns:
        List of 1-based sentence boundary indices.
    """
    n = len(sentences)
    if n < 3:
        return []

    tfs = [_tf(_tokenize(s)) for s in sentences]

    # Build cosine similarity matrix
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        sim[i][i] = 1.0
        for j in range(i + 1, n):
            v = _cosine(tfs[i], tfs[j])
            sim[i][j] = v
            sim[j][i] = v

    # Rank-transform within local window
    rank = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            r_lo = max(0, i - window)
            r_hi = min(n, i + window + 1)
            c_lo = max(0, j - window)
            c_hi = min(n, j + window + 1)
            local = [sim[r][c] for r in range(r_lo, r_hi) for c in range(c_lo, c_hi)]
            local_sorted = sorted(local)
            try:
                pos = local_sorted.index(sim[i][j])
            except ValueError:
                pos = 0
            rank[i][j] = (pos + 1) / len(local) if local else 0.0

    # Compute column-sum difference (boundary strength) between adjacent sentences
    scores: list[float] = []
    for k in range(1, n):
        before = sum(rank[i][j] for i in range(k) for j in range(k))
        after = sum(rank[i][j] for i in range(k, n) for j in range(k, n))
        size_b = k * k
        size_a = (n - k) * (n - k)
        score = (before / size_b if size_b else 0) + (after / size_a if size_a else 0)
        scores.append(score)

    if not scores:
        return []

    if n_segments is not None:
        # Pick top (n_segments - 1) valleys = lowest coherence breaks
        n_boundaries = max(0, n_segments - 1)
        # Boundary = low internal coherence sum => pick valleys
        indexed = sorted(enumerate(scores), key=lambda x: x[1])
        boundary_indices = sorted(idx + 1 for idx, _ in indexed[:n_boundaries])
    else:
        mean = sum(scores) / len(scores)
        std = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores))
        threshold = mean - std_coeff * std
        boundary_indices = [i + 1 for i, s in enumerate(scores) if s < threshold]

    return [b for b in boundary_indices if 0 < b < n]
