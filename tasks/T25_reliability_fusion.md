# T25 — Reliability-Weighted Fusion Module (Novelty N2)

**Phase 7 · Novel Method · Estimated time: 6 h · Owner: Ismam**

---

## 🎯 What you are doing
Building the **first of our four novel modules**: a small neural layer that takes per-modality "boundary evidence" (text, visual, prosody, OCR) at every sentence position, and outputs a **learned weight** for each modality based on how reliable it appears for this specific video.

## 🤔 Why
Prior multimodal work (Yu 2024, PreMind) fuses modalities with fixed weights. When a lecturer is chalkboard-only, the visual channel is useless — a fixed weight wastes it. When a speaker has heavy accent, the text channel is noisy — fixed weights over-trust it. Our module learns, per sentence, which modality to listen to. **This is novelty N2.**

## ✅ How to know you are done
- `src/lecseg/models/rw_fusion.py` defines `ReliabilityWeightedFusion(nn.Module)`.
- `tests/test_rw_fusion.py` verifies: forward pass works, output is normalised, gradient flows.
- A minimal-data smoke run on 3 videos outperforms a fixed-weight baseline by > 1 point WD.

---

## 📝 Steps

### Ask Claude

> Execute T25. First read `docs/NOVELTY_TRACKER.md` N2 entry. Write `src/lecseg/models/rw_fusion.py`.
>
> **Architecture:**
> - Input: per-sentence features `(B, T, M, D)` where M = 4 modalities (text, visual, prosody, OCR).
> - A **reliability scorer** — a small MLP `(D → 64 → 1)` per modality that outputs a scalar reliability `r_m` at each time step.
> - Reliability is passed through softmax over M → gates `g_m(t)`.
> - Output: `fused(t) = sum_m g_m(t) · feat_m(t)`.
>
> Expose: `forward(x)` and `forward_with_gates(x) -> (fused, gates)` for analysis.
>
> Also write `scripts/smoke_fusion.py`: train on 25 videos, eval on 5, compare to a fixed-equal-weight baseline.

### Verify

```
python -m pytest tests/test_rw_fusion.py -v
python scripts/smoke_fusion.py --videos 3
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Fusion** | Combining information from multiple sources into one. |
| **Gate** | A learned multiplier (between 0 and 1) that controls how much a signal contributes. |
| **Reliability** | How trustworthy each modality looks at this moment. Learned, not preset. |
| **Softmax** | Turns any vector of numbers into probabilities that sum to 1. |

More: [docs/CONCEPTS.md#fusion](../docs/CONCEPTS.md#fusion)

---

## ➡️ When done

```
python scripts/mark_done.py T25
python scripts/update_thesis.py T25
python scripts/today.py
```
