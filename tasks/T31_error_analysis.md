# T31 — Qualitative Error Analysis

**Phase 8 · Evaluation · Estimated time: 4 h · Owner: Sadia**

---

## 🎯 What you are doing
Going through the per-video predictions and writing down **where the model fails and why**. This gives us 3–5 concrete "failure cases" for Chapter 4's discussion section, and 2–3 "future work" bullets for Chapter 5.

## ✅ How to know you are done
- `docs/ERROR_ANALYSIS.md` lists 5 categories of failure with 1 example each + proposed fix.
- Each example links to a figure in `results/figures/`.

---

## 📝 Steps

### Ask Claude

> Execute T31. Read `results/ablations/predictions.jsonl` for our-best method.
>
> Bucket failures by:
> 1. False positives (model predicts a boundary that isn't in GT)
> 2. False negatives (model misses a GT boundary)
> 3. Off-by-more-than-60s boundaries
> 4. Chalkboard-lecture visual-channel noise
> 5. Accented-speaker text-channel noise
>
> For each category, print the top-3 worst videos with context (a window of sentences around the boundary) and save to `results/error_cases/<category>.jsonl`. Also make a timeline figure per category (horizontal bar showing GT vs pred) in `results/figures/err_<category>.png`.

### Step 2 — Human review

Read each failure and decide:
- **Model bug?** → file a follow-up fix task and either fix or document it.
- **Data issue?** → note as a dataset limitation in Chapter 5.
- **Edge case?** → document as future-work opportunity.

Write up 5 categories, one short paragraph each, in `docs/ERROR_ANALYSIS.md`.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **False positive** | You predicted a boundary there wasn't. Makes chapters too small. |
| **False negative** | You missed a boundary that was there. Makes chapters too big. |
| **Error analysis** | Going through the model's mistakes by hand to understand patterns. |

---

## ➡️ When done

```
python scripts/mark_done.py T31
python scripts/update_thesis.py T31
python scripts/today.py
```
