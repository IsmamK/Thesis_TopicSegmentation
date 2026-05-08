# T19 — Text Embeddings (SBERT / MPNet / E5 / BGE)

**Phase 5 · Features · Estimated time: 2 h · Owner: Ismam**

---

## 🎯 What you are doing
Turning every sentence into a **vector** (a list of numbers) that captures its meaning. Sentences about the same topic produce similar vectors; different topics produce different vectors. This is the core input to the segmentation model.

We compute four embedding families so we can benchmark them: SBERT (MiniLM), MPNet, E5, BGE.

## ✅ How to know you are done
- `data/emb_text/<video_id>_<model>.npy` exists for all 30 videos × 4 models.
- Shape: `(n_sentences, emb_dim)` with dtype float32.

---

## 📝 Steps

### Ask Claude

> Execute T19. Write `src/lecseg/features/text_emb.py` and `scripts/embed_text.py`.
>
> Models (use sentence-transformers):
>   - `all-MiniLM-L6-v2` (384 dim)
>   - `all-mpnet-base-v2` (768 dim)
>   - `intfloat/e5-base-v2` (768 dim) — prepend "passage: " to the text.
>   - `BAAI/bge-base-en-v1.5` (768 dim)
>
> For each video × model:
> 1. Read sentences from `data/sentences/<id>.jsonl`.
> 2. Encode with `model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)`.
> 3. Save to `data/emb_text/<id>_<model_tag>.npy`.
>
> Idempotent. Auto-uses GPU if available.

### Verify

```
python -c "import numpy as np; x = np.load('data/emb_text/<id>_minilm.npy'); print(x.shape, x.dtype, x[0][:5])"
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Embedding** | A list of numbers (usually 384 or 768) that represents a sentence's meaning. |
| **SBERT (Sentence-BERT)** | The most common way to produce sentence embeddings. Reimers & Gurevych 2019. |
| **MPNet** | A stronger base model than MiniLM. Bigger but better. |
| **E5 / BGE** | More recent embedding families, often top-scoring on MTEB leaderboard. |
| **Normalized** | Vector length = 1. Makes cosine similarity == dot product (faster). |

More: [docs/CONCEPTS.md#text-embeddings](../docs/CONCEPTS.md#text-embeddings)

---

## ➡️ When done

```
python scripts/mark_done.py T19
python scripts/today.py
```
