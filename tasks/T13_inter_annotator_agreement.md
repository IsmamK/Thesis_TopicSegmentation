# T13 — Compute Inter-Annotator Agreement (Cohen's Kappa)

**Phase 3 · Dataset · Estimated time: 45 min · Owner: Shahriar**

---

## 🎯 What you are doing
Given the 10 dual-annotated videos from T12, compute how much the two annotators agreed on boundary placement. Produce a single number (Cohen's κ) per video, then an overall mean and 95% confidence interval.

## 🤔 Why
If humans don't agree on where subtopic boundaries go, no model can be expected to. A κ > 0.6 is "substantial" and acceptable for publication. Below 0.4, we revise our annotation guidelines and re-annotate.

## ✅ How to know you are done
- `results/kappa/kappa.csv` has 10 rows (one per dual-annotated video).
- `results/kappa/summary.md` has: mean κ, std, 95% CI, per-level breakdown (chapter vs subtopic).
- Mean κ ≥ 0.60 (substantial agreement).

---

## 📝 Steps

### Step 1 — Ask Claude

> Execute T13. Write `src/lecseg/eval/kappa.py` and `scripts/compute_kappa.py`.
> 
> For each of the 10 dual-annotated videos:
> 1. Read both annotations (`data/gt_hier/<id>.json` and `data/gt_hier/double/<id>.json`).
> 2. Discretize the video timeline into 1-second bins.
> 3. Label each bin as boundary (1) or not (0) for each annotator (tolerance window = ±5 s for chapter, ±3 s for subtopic).
> 4. Compute Cohen's κ using `sklearn.metrics.cohen_kappa_score`, separately for chapter-level and subtopic-level.
> 5. Save per-video and overall results with bootstrap 95% CIs (n=1000 resamples) to `results/kappa/kappa.csv` and `results/kappa/summary.md`.

### Step 2 — Interpret the result

Read `results/kappa/summary.md` and check the mean κ:

| κ value | What it means | Action |
|---|---|---|
| ≥ 0.80 | Almost perfect | Excellent. |
| 0.60–0.79 | Substantial | Good. Mention in thesis with confidence. |
| 0.40–0.59 | Moderate | Acceptable but flag weakness. Refine guidelines. |
| 0.20–0.39 | Fair | Problem. Re-discuss guidelines (T12 Step 2), re-annotate disagreed videos. |
| < 0.20 | Slight | Stop. The task is ill-defined. Regroup with supervisor. |

If κ < 0.60, we iterate before moving on.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Cohen's κ (kappa)** | A number from -1 to +1 that measures agreement between two raters, adjusted for chance. 0 = random-level agreement; 1 = perfect. |
| **Bootstrap CI** | We resample the data with replacement 1000 times and recompute κ each time. The spread of those 1000 values gives a confidence interval. |
| **Tolerance window** | Humans can't mark boundaries to the second. We say two boundaries "agree" if they are within ±5 s. |

More: [docs/CONCEPTS.md#agreement](../docs/CONCEPTS.md#agreement)

---

## ➡️ When done

```
python scripts/mark_done.py T13
python scripts/update_thesis.py T13   # updates Chapter 3 with κ number
python scripts/today.py
```
