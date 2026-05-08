# T23 — Classical Baselines (TextTiling, C99)

**Phase 6 · Baselines · Estimated time: 3 h · Owner: Shahriar**

---

## 🎯 What you are doing
Implementing two 1990s/2000s classical text-only baselines so Chapter 4 has something to beat. TextTiling (Hearst 1997) and C99 (Choi 2000) are the reference baselines for any segmentation paper.

## ✅ How to know you are done
- `src/lecseg/models/baselines/text_tiling.py` and `c99.py` exist.
- `scripts/run_baselines.py` runs both on all 30 videos.
- `results/baselines_classical/metrics.json` has per-video and mean Pk/WD/BS.

---

## 📝 Steps

### Ask Claude

> Execute T23. Write `src/lecseg/models/baselines/text_tiling.py` and `c99.py`, using `nltk.tokenize.TextTilingTokenizer` for TextTiling and `choi_segmenter.py` (port from Choi's Python) for C99. Hyper-params via Hydra:
>   - TextTiling: `k` (pseudosentence length), `w` (window size).
>   - C99: `ngram`, `stopword_set`, `rank_mask_size`.
>
> For each video:
> 1. Read sentences (T15).
> 2. Feed joined text to the baseline.
> 3. Convert segment outputs back to **sentence-index** boundaries.
> 4. Convert sentence-index boundaries to **seconds** using the sentence timeline.
> 5. Compute Pk, WD, BS, tolerance-F1 vs GT (from T11).
> 6. Save per-video metrics, predictions, and config to `results/YYYYMMDD_HHMM_texttiling/` and `results/YYYYMMDD_HHMM_c99/`.

### Verify

```
python -c "import json; print(json.load(open('results/<latest>/metrics.json')))"
python scripts/interpret.py results/<latest>/metrics.json
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **TextTiling** | Slide a window across the text; where cosine similarity drops sharply, put a boundary. Hearst 1997. |
| **C99** | Compute a sentence-similarity matrix, apply divisive clustering on its blocks. Choi 2000. |
| **Hydra** | A config-management library. Lets us write `k=10` in a YAML file. |

More: [docs/CONCEPTS.md#baselines](../docs/CONCEPTS.md#baselines)

---

## ➡️ When done

```
python scripts/mark_done.py T23
python scripts/today.py
```
