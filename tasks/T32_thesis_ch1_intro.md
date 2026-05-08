# T32 — Thesis Chapter 1: Introduction

**Phase 9 · Thesis Writing · Estimated time: 1 day · Owner: Sadia**

---

## 🎯 What you are doing
Writing Chapter 1 (~8 pages) covering: the problem, motivation, objectives, research questions, our contributions, and the thesis outline. This is the chapter the panel reads first.

## ✅ How to know you are done
- `thesis/chapters/chapter1_introduction.tex` compiles inside `main.tex`.
- Chapter is **8–10 pages** (±1 OK).
- All 7 novelty claims (N1–N7) are listed in Section 1.4 "Contributions".
- Every forward-reference is correct (`\cref{sec:method}` resolves).

---

## 📝 Steps

### Ask Claude

> Execute T32. Write `thesis/chapters/chapter1_introduction.tex`. Structure:
>
> - **1.1 Background & motivation** — why lecture video segmentation matters (accessibility, navigation, indexing, online education post-COVID). Cite recent stats.
> - **1.2 Problem statement** — no open, hierarchical, reproducible lecture segmentation system exists. Prior work is closed (PreMind), flat (AVLectures), or text-only (classical).
> - **1.3 Research questions (RQ1–RQ5)** — match `docs/NOVELTY_TRACKER.md`.
> - **1.4 Contributions** — bullet list of N1–N7 with 1 sentence each.
> - **1.5 Thesis outline** — summarise chapters 2–6.
>
> Voice: passive / collective ("we design…", "we show…"). **No first-person "I".** **No mention of AI tools.**
>
> All citations via `\cite{<bibkey>}`; figures saved to `thesis/figures/ch1_*.pdf`.

### Step 2 — Review

Read it once. Ask: does the non-technical reader understand the problem by page 3?

### Step 3 — Compile

```
cd thesis && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Check `thesis/main.pdf` renders Chapter 1 without overfull hboxes or missing citations.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Motivation section** | Why should the reader care? 2 paragraphs minimum, citing recent numbers. |
| **Research question** | A falsifiable question the thesis answers. E.g., "Can reliability-weighted fusion outperform fixed fusion on lecture videos?" |
| **Contributions** | The specific artefacts/claims this thesis delivers. Must match what the code + paper produce. |

More: [docs/THESIS_WRITING_GUIDE.md](../docs/THESIS_WRITING_GUIDE.md)

---

## ➡️ When done

```
python scripts/mark_done.py T32
python scripts/today.py
```
