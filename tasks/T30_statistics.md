# T30 — Bootstrap 95% CIs + Paired Wilcoxon Tests

**Phase 8 · Evaluation · Estimated time: 3 h · Owner: Shahriar**

---

## 🎯 What you are doing
For every method in T29, compute a **95% confidence interval** via bootstrap (n=1000 video-level resamples), and a **paired Wilcoxon signed-rank test** comparing our best model against each baseline. Without this, panel members will ask "but is the improvement significant?" and we won't have an answer. **This is novelty N6.**

## ✅ How to know you are done
- `results/ablations/statistics.csv` has CIs for every method × metric.
- `results/ablations/significance.csv` has p-value for (our-best vs each baseline) × each metric.
- p < 0.05 for at least the main comparison (Ours-all-hier+LLM vs best baseline on H-WD).

---

## 📝 Steps

### Ask Claude

> Execute T30. Write `src/lecseg/eval/stats.py` and `scripts/run_statistics.py`.
>
> Input: per-video metrics from T29.
>
> For each (method, metric):
>   - Bootstrap 1000× resample of the 30 videos with replacement; recompute mean; take 2.5/97.5 percentiles → 95% CI.
>
> For each comparison (Ours-all-hier+LLM vs method X, for each metric):
>   - Paired Wilcoxon signed-rank over the 30 per-video values (scipy.stats.wilcoxon).
>   - Report p-value; flag p<0.05 (★), p<0.01 (★★), p<0.001 (★★★).
>
> Export `statistics.csv` and `significance.csv`.

### Verify

```
python scripts/interpret.py results/ablations/significance.csv
```

If p ≥ 0.05 against the strongest baseline, the story needs care. Tell the thesis prose that the improvement is visible in effect size but does not reach statistical significance at n=30.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **95% CI** | A range such that, if we re-ran the experiment many times, the true mean would land in that range 95% of the time. |
| **Bootstrap** | Re-sampling with replacement from our own data 1000 times to estimate uncertainty without parametric assumptions. |
| **Wilcoxon signed-rank** | A non-parametric paired test. Robust when data is not normal (segmentation metrics rarely are). |

More: [docs/CONCEPTS.md#statistics](../docs/CONCEPTS.md#statistics)

---

## ➡️ When done

```
python scripts/mark_done.py T30
python scripts/update_thesis.py T30
python scripts/today.py
```
