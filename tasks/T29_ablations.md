# T29 — Run Full Ablation Battery

**Phase 8 · Evaluation · Estimated time: 1 day unattended + 4 h analysis · Owner: Shahriar**

---

## 🎯 What you are doing
Running the full experiment matrix: **every baseline × every variant of our model**. Each row produces metrics under `results/`. At the end, we have a table like Table 4 in any conference paper.

## ✅ How to know you are done
- `results/ablations/master_table.csv` exists with every method × every metric.
- Each method has a row with mean ± std across 5 folds.
- A figure `results/ablations/fig_comparison.pdf` compares methods visually.

---

## 📝 Steps

### Ask Claude

> Execute T29. Write `scripts/run_ablations.py` that runs every combination below and writes the aggregated table.
>
> **Methods matrix:**
>
> | # | Method | Modality | Refinement |
> |---|---|---|---|
> | 1 | TextTiling | text | — |
> | 2 | C99 | text | — |
> | 3 | Cosine-drop | text-emb | — |
> | 4 | KMeans-seg | text-emb | — |
> | 5 | Ours-textonly | text-emb | none |
> | 6 | Ours-text+visual | text+visual | none |
> | 7 | Ours-text+visual+prosody | 3 modalities | none |
> | 8 | Ours-all (fixed weights) | 4 modalities | none |
> | 9 | Ours-all (N2 RW-fusion) | 4 modalities | none |
> | 10 | Ours-all-hier (+N3) | 4 modalities | none |
> | 11 | Ours-all-hier+LLM (+N4) | 4 modalities | LLM |
> | 12 | Ours-all-hier+LLM (no local cache) | 4 modalities | LLM no cache |
>
> For each row: 5-fold CV, output metrics.json, config.yaml, git_sha.txt, predictions.jsonl.
>
> Aggregate into a single `master_table.csv` with columns: method, pk_mean, pk_std, wd_mean, wd_std, bs_mean, bs_std, tolf1_mean, tolf1_std, hwd_mean, hwd_std.

### Verify

```
python scripts/interpret.py results/ablations/master_table.csv
```

Expect to see monotonic improvement as we add modalities. If a row regresses, flag it (e.g., visual may hurt on chalkboard-only videos — that's okay, we analyse in T31).

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Ablation** | Turning off one component at a time to isolate its contribution. |
| **5-fold CV** | Split videos into 5 groups; train on 4, test on 1, rotate, average. |
| **Master table** | The one table that summarises all methods and all metrics. The centerpiece of Chapter 4. |

More: [docs/CONCEPTS.md#ablations](../docs/CONCEPTS.md#ablations)

---

## ➡️ When done

```
python scripts/mark_done.py T29
python scripts/update_thesis.py T29
python scripts/today.py
```
