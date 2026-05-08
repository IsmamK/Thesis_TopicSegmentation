# T22 — Metrics Library (Pk, WD, BS, H-WD, Tolerance-F1)

**Phase 6 · Baselines · Estimated time: 3 h · Owner: Shahriar**

---

## 🎯 What you are doing
Writing a single module `src/lecseg/eval/metrics.py` that computes all 5 segmentation metrics we will use throughout the project. One function per metric. Every baseline and our novel model funnel results through this module — guaranteeing apples-to-apples comparison.

## ✅ How to know you are done
- `src/lecseg/eval/metrics.py` implements 5 functions: `pk`, `window_diff`, `boundary_similarity`, `hierarchical_wd`, `tolerance_f1`.
- `tests/test_metrics.py` contains ≥ 3 tests per metric including edge cases (empty, all-boundary, single-boundary).
- All tests pass.

---

## 📝 Steps

### Ask Claude

> Execute T22. Write `src/lecseg/eval/metrics.py` and `tests/test_metrics.py`.
>
> Use `segeval` for Pk/WD/BS (they are standard); write tolerance_f1 and hierarchical_wd from scratch. Input/output contract:
>
> ```python
> pk(pred_boundaries, gt_boundaries, sequence_length) -> float
> window_diff(pred, gt, n) -> float
> boundary_similarity(pred, gt) -> float
> tolerance_f1(pred_secs, gt_secs, tolerance_sec: float) -> dict  # {precision, recall, f1}
> hierarchical_wd(pred_hier, gt_hier, n) -> dict  # {chapter_wd, subtopic_wd, h_wd}
> ```
>
> Where `pred_hier = {"chapter": [b1,b2,...], "subtopic": [b1,...]}`.
>
> For `hierarchical_wd`, compute WD on the chapter-level and WD on the subtopic-level, weight them (chapter 2×, subtopic 1×), and return the weighted average.
>
> Tests should cover:
> - Perfect agreement → metric = 0 for Pk/WD, 1 for BS/F1.
> - Zero agreement → metric = 1 for Pk/WD, 0 for BS/F1.
> - Off-by-one boundary with tolerance=5s → F1 = 1 still.
> - Mixed real examples.

---

## 🧠 Concepts

| Metric | Plain-English meaning | Interpretation |
|---|---|---|
| **Pk** | A random window of words falls across a wrong boundary with probability Pk. | Lower = better. <0.3 strong. |
| **WD (WindowDiff)** | Like Pk, but penalises over/under-segmentation too. | Lower = better. |
| **BS (Boundary Similarity)** | Fournier 2013 metric, robust to near-misses. | Higher = better. 1 = perfect. |
| **Tolerance-F1** | F1 on boundaries with a ±N-second tolerance. | Higher = better. |
| **H-WD (Hierarchical WD)** | Weighted sum of chapter- and subtopic-level WD. **Our novelty N6.** | Lower = better. |

More: [docs/CONCEPTS.md#metrics](../docs/CONCEPTS.md#metrics)

---

## ➡️ When done

```
python scripts/mark_done.py T22
python scripts/today.py
```
