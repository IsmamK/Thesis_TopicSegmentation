# T35 — Thesis Chapter 4: Results & Analysis

**Phase 9 · Thesis Writing · Estimated time: 2 days · Owner: Sadia + Shahriar**

---

## 🎯 What you are doing
Reporting every number from T29–T31 in clean tables and figures, followed by a discussion that turns numbers into insight. ~15 pages.

## ✅ How to know you are done
- `thesis/chapters/chapter4_results.tex` compiles, 12–18 pages.
- Master table (from T29) reproduced as LaTeX table with bolded best entries.
- At least 4 figures: per-method comparison bar chart, ablation curve, H-WD by domain, one qualitative per-video timeline.
- Significance stars from T30 appear next to significant improvements.

---

## 📝 Steps

### Ask Claude

> Execute T35. Read `results/ablations/master_table.csv`, `statistics.csv`, `significance.csv`, and `docs/ERROR_ANALYSIS.md`.
>
> Write `thesis/chapters/chapter4_results.tex`:
>
> - **4.1 Experimental setup** — hardware, seed, fold split, training budget.
> - **4.2 Baseline comparison** — Table (LaTeX) with mean±95%CI for every method × metric; bold best.
> - **4.3 Ablation study** — Which modality contributes most? Fig showing H-WD as we add modalities.
> - **4.4 Reliability-weighted fusion analysis (N2)** — gate visualisation on 2–3 videos.
> - **4.5 Hierarchical output quality (N3)** — subtopic-level metrics, per-domain.
> - **4.6 LLM refinement contribution (N4)** — with-LLM vs without.
> - **4.7 Statistical significance** — Wilcoxon table with stars.
> - **4.8 Qualitative error analysis** — 5 failure cases (from T31).
> - **4.9 Discussion** — honest limitations and open questions.
>
> Use `\cite{<key>}` for every baseline reference.

### Verify

Every number in prose matches the corresponding number in `results/ablations/master_table.csv`. No cherry-picking.

---

## ➡️ When done

```
python scripts/mark_done.py T35
python scripts/today.py
```
