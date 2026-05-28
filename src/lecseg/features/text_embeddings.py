"""
T19 — Text embeddings for lecture sentences.

Supported models (auto-downloaded on first use):
    sbert   — all-MiniLM-L6-v2     (fast, 384-dim)
    mpnet   — all-mpnet-base-v2    (best quality, 768-dim)
    e5      — intfloat/e5-base-v2  (instruction-tuned, 768-dim)
    bge     — BAAI/bge-base-en-v1.5 (SOTA retrieval, 768-dim)

Usage:
    from lecseg.features.text_embeddings import embed_sentences, embed_file

    vecs = embed_sentences(["sentence one", "sentence two"], model="mpnet")
    # vecs: np.ndarray shape (N, D), float32, L2-normalised
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path

MODEL_NAMES = {
    "sbert":  "sentence-transformers/all-MiniLM-L6-v2",
    "mpnet":  "sentence-transformers/all-mpnet-base-v2",
    "e5":     "intfloat/e5-base-v2",
    "bge":    "BAAI/bge-base-en-v1.5",
}

_cache: dict[str, object] = {}


def _get_model(model_key: str):
    from sentence_transformers import SentenceTransformer
    if model_key not in _cache:
        name = MODEL_NAMES.get(model_key, model_key)
        _cache[model_key] = SentenceTransformer(name)
    return _cache[model_key]


def embed_sentences(
    sentences: list[str],
    model: str = "mpnet",
    batch_size: int = 64,
    normalize: bool = True,
    prefix: str = "",
) -> np.ndarray:
    """
    Embed a list of sentences.

    Args:
        sentences:  list of sentence strings
        model:      one of 'sbert', 'mpnet', 'e5', 'bge' or a HF model ID
        batch_size: encoding batch size
        normalize:  L2-normalise output vectors
        prefix:     prepend this to each sentence (e5/bge use "query: " prefix)

    Returns:
        np.ndarray of shape (len(sentences), dim), dtype float32
    """
    if not sentences:
        return np.zeros((0, 1), dtype=np.float32)

    m = _get_model(model)
    texts = [prefix + s for s in sentences] if prefix else sentences

    vecs = m.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    return vecs.astype(np.float32)


def embed_file(
    sentences_json: Path | str,
    out_path: Path | str | None = None,
    model: str = "mpnet",
    batch_size: int = 64,
) -> np.ndarray:
    """
    Embed all sentences from a sentences.json file.

    Args:
        sentences_json: path to sentences.json (from T15)
        out_path:       where to save embeddings as .npy (None = don't save)
        model:          embedding model key
        batch_size:     batch size for encoding

    Returns:
        np.ndarray of shape (N, D)
    """
    sentences_json = Path(sentences_json)
    data = json.loads(sentences_json.read_text(encoding="utf-8"))
    texts = [s["text"] for s in data.get("sentences", [])]

    # e5 and bge work best with a query prefix for retrieval; for encoding use passage prefix
    prefix = ""
    if model == "e5":
        prefix = "passage: "
    elif model == "bge":
        prefix = ""  # bge-base doesn't need prefix for encoding

    vecs = embed_sentences(texts, model=model, batch_size=batch_size, prefix=prefix)

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(out_path), vecs)

    return vecs


def embed_all(
    sentences_dir: Path | str = "data/sentences",
    embeddings_dir: Path | str = "data/embeddings",
    model: str = "mpnet",
    force: bool = False,
) -> dict[str, tuple[int, int]]:
    """
    Embed all sentence files under sentences_dir.

    Returns:
        Dict mapping video_id -> (n_sentences, embedding_dim)
    """
    sentences_dir = Path(sentences_dir)
    embeddings_dir = Path(embeddings_dir)
    results: dict[str, tuple[int, int]] = {}

    for sfile in sorted(sentences_dir.glob("*/sentences.json")):
        video_id = sfile.parent.name
        out_npy = embeddings_dir / model / video_id / "embeddings.npy"

        if out_npy.exists() and not force:
            vecs = np.load(str(out_npy))
            results[video_id] = (vecs.shape[0], vecs.shape[1])
            continue

        vecs = embed_file(sfile, out_path=out_npy, model=model)
        results[video_id] = (vecs.shape[0], vecs.shape[1] if vecs.ndim > 1 else 0)
        print(f"  {video_id}: {vecs.shape} [{model}]")

    return results


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "mpnet"
    print(f"Embedding all sentences with model={model}")
    results = embed_all(model=model)
    print(f"\nDone. {len(results)} videos embedded.")
