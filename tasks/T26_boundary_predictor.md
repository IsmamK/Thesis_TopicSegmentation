# T26 — Two-Stage Boundary Predictor (Novelty N1)

**Phase 7 · Novel Method · Estimated time: 8 h · Owner: Ismam**

---

## 🎯 What you are doing
Stage 1 is a per-sentence **boundary score** from the fused representation (T25). Stage 2 is a **sequence-level refinement** that enforces global coherence: no two boundaries can be within 60 s; a chapter cannot be longer than 30 min; etc.

## ✅ How to know you are done
- `src/lecseg/models/boundary_predictor.py` with a training loop.
- Checkpoints under `results/<exp>/checkpoints/`.
- Mean chapter-level WD across 30 videos beats the best baseline by ≥ 2 points.

---

## 📝 Steps

### Ask Claude

> Execute T26. Two stages:
>
> **Stage 1 (local):** A BiLSTM or Transformer encoder over the fused feature sequence from T25. Output: logits per sentence for `P(boundary | features)`.
>
> **Stage 2 (global):** Viterbi-style dynamic-programming decoder that enforces:
>   - `min_chapter_length_sec = 120`
>   - `max_chapter_length_sec = 1800`
>   - Hard caps: `K_min = 3, K_max = 15` per video.
>
> Training: 5-fold cross-validation at the video level (24 train, 6 val per fold). Loss = binary cross-entropy with positive class up-weighting (rare event). Optimiser AdamW, lr 1e-4, 30 epochs, early stop on val WD.
>
> Track metrics per epoch; save best checkpoint; final eval on all 30 with 5-fold averaging.

### Verify

```
python scripts/run_boundary.py --seed 42
python scripts/interpret.py results/<latest>/metrics.json
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **BiLSTM** | Bidirectional Long Short-Term Memory. A neural net that reads a sequence forwards and backwards. |
| **Viterbi decoding** | A dynamic-programming algorithm that finds the most probable sequence subject to constraints. |
| **Cross-validation** | Train on part, evaluate on the rest, rotate. Gives robust estimates from small data. |

More: [docs/CONCEPTS.md#boundary-prediction](../docs/CONCEPTS.md#boundary-prediction)

---

## ➡️ When done

```
python scripts/mark_done.py T26
python scripts/update_thesis.py T26
python scripts/today.py
```
