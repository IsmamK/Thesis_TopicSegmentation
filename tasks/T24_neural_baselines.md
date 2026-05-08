# T24 — Neural Baselines (Cosine, KMeans, BERT-SegBot)

**Phase 6 · Baselines · Estimated time: 4 h · Owner: Shahriar**

---

## 🎯 What you are doing
Three stronger 2019+ baselines: (1) sentence-embedding cosine-drop, (2) KMeans over embeddings, (3) a supervised neural model (SegBot / BERT-seg) if time permits.

## ✅ How to know you are done
- `src/lecseg/models/baselines/cosine_drop.py`, `kmeans_seg.py`, `bert_segbot.py` exist.
- Each has a results folder under `results/` with metrics.

---

## 📝 Steps

### Ask Claude

> Execute T24. Three baselines:
>
> **a) Cosine drop** — Using SBERT vectors (T19), compute cosine similarity between sentence i and i+1. Place a boundary where the drop exceeds threshold `τ` (tuned on 5 held-out videos). Write `cosine_drop.py`.
>
> **b) KMeans segmentation** — Stack all sentence embeddings, cluster with K=expected num chapters (from config). A boundary = cluster label changes between consecutive sentences. Write `kmeans_seg.py`.
>
> **c) BERT-SegBot-like** — If the supervised training budget is tight, skip this in T24 and implement in T26 instead. If doing here: fine-tune a small head on top of frozen SBERT to predict per-sentence {boundary, not-boundary}.
>
> All three share the same config template: `configs/baselines/<name>.yaml`.

### Verify

Run all three and print their mean Pk/WD. Compare to T23 classical baselines. The neural ones should be slightly better.

```
python scripts/run_baselines.py --models cosine_drop kmeans_seg
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Cosine similarity** | A number from -1 to 1 measuring how similar two vectors are. |
| **KMeans** | A clustering algorithm: group data into K clusters by minimising within-cluster distance. |
| **SegBot** | A 2018 neural text-segmenter (Li et al.) using pointer networks. |
| **Held-out set** | A slice of data used only for tuning hyper-params, never for training or final eval. |

---

## ➡️ When done

```
python scripts/mark_done.py T24
python scripts/today.py
```
