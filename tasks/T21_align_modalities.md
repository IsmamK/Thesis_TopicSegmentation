# T21 — Align All Modalities to the Sentence Timeline

**Phase 5 · Features · Estimated time: 2 h · Owner: Ismam**

---

## 🎯 What you are doing
Every feature lives on its own timeline (sentences per-sentence, shots per-shot, prosody per-sentence, OCR per-shot). We resample everything to the **sentence timeline** so each sentence has: its text vector, the visual vector of the shot it falls inside, its prosody, the OCR text of that shot.

This is the single matrix that every model consumes.

## ✅ How to know you are done
- `data/features/<video_id>.parquet` exists for all 30 videos, one row per sentence.
- Columns: `idx, start_sec, end_sec, text, text_emb, visual_emb, ocr_text, ocr_emb, pause_before_sec, pitch_delta_hz, rate_delta_wpm`.

---

## 📝 Steps

### Ask Claude

> Execute T21. Write `src/lecseg/features/align.py` and `scripts/build_features.py`.
>
> For each video:
> 1. Load sentences (T15), text embeddings (T19), shots (T16), visual embeddings (T20), OCR (T17), prosody (T18).
> 2. For each sentence i:
>    - Find the shot j such that shots[j].start <= sentence[i].start < shots[j+1].start.
>    - Attach visual_emb[j] and ocr_text[j].
>    - Attach prosody[i].
> 3. Write a parquet file with arrays stored as float32 buffers.
>
> Also compute an OCR embedding: pass ocr_text through the MiniLM encoder (T19) and store `ocr_emb`.

### Verify

```
python -c "import pandas as pd; df = pd.read_parquet('data/features/<id>.parquet'); print(df.shape); print(df.columns.tolist())"
```

Row count = number of sentences. All columns present. No NaNs in text_emb / visual_emb.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Timeline alignment** | Making features from different sources line up second-to-second. |
| **Parquet** | A columnar binary file format. Fast to read/write, smaller than CSV. |

More: [docs/CONCEPTS.md#alignment](../docs/CONCEPTS.md#alignment)

---

## ➡️ When done

```
python scripts/mark_done.py T21
python scripts/today.py
```
