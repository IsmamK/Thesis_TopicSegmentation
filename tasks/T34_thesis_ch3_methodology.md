# T34 — Thesis Chapter 3: Methodology

**Phase 9 · Thesis Writing · Estimated time: 2 days · Owner: Sadia + Ismam**

---

## 🎯 What you are doing
The **biggest and most important chapter** (~20 pages): describe the dataset (LECSEG-30), the preprocessing pipeline, the four novel modules (N1–N4), and the evaluation protocol.

## ✅ How to know you are done
- `thesis/chapters/chapter3_methodology.tex` is 18–25 pages.
- Contains at least 3 figures: the pipeline overview, the fusion architecture, the hierarchical decoder.
- Every module in `src/lecseg/` is described in prose with a pseudocode block.
- Dataset section reports κ from T13 and summary stats from `data/gt/gt_summary.csv`.

---

## 📝 Steps

### Ask Claude

> Execute T34. Write `thesis/chapters/chapter3_methodology.tex` with:
>
> - **3.1 Overview** — 1-page overview with the pipeline figure (`\includegraphics{pipeline_overview.pdf}`).
> - **3.2 LECSEG-30 dataset** — size, domains, κ, annotation protocol, collection ethics.
> - **3.3 Preprocessing** — transcription (T14), sentence splitting (T15), shot boundaries (T16), OCR (T17), prosody (T18), alignment (T21).
> - **3.4 Feature extraction** — text embeddings (T19), visual embeddings (T20).
> - **3.5 Reliability-weighted fusion (N2)** — architecture diagram + formula.
> - **3.6 Two-stage boundary predictor (N1)** — local scorer + Viterbi decoder.
> - **3.7 Hierarchical decoder (N3)** — dual-head + nesting constraint.
> - **3.8 LLM boundary refinement (N4)** — prompt template + caching.
> - **3.9 Evaluation protocol (N6)** — metrics (Pk, WD, BS, tol-F1, H-WD), 5-fold CV, bootstrap CIs, Wilcoxon.
> - **3.10 Reproducibility (N7)** — `make reproduce`, config system, seed management.
>
> Every number must be sourced: either from code config or from `docs/METHODOLOGY.md`.

### Verify

Chapter compiles. All figures render. No `[?]` citations.

---

## ➡️ When done

```
python scripts/mark_done.py T34
python scripts/today.py
```
