# T33 — Thesis Chapter 2: Literature Review

**Phase 9 · Thesis Writing · Estimated time: 1 day · Owner: Sadia**

---

## 🎯 What you are doing
Turning `docs/LITERATURE_MATRIX.md` (from T07) into prose: ~12 pages of structured critical review organised by theme, ending with a **Gap Analysis section** that motivates our 7 novelties.

## ✅ How to know you are done
- `thesis/chapters/chapter2_literature.tex` compiles, 10–15 pages.
- At least 20 citations resolved from `thesis/bibliography/references.bib`.
- Section 2.6 "Gap Analysis" maps each gap to N1–N7.

---

## 📝 Steps

### Ask Claude

> Execute T33. Read `docs/LITERATURE_MATRIX.md` and every file in `papers_summary/`. Write `thesis/chapters/chapter2_literature.tex` with these sections:
>
> - **2.1 Classical text segmentation** (TextTiling, C99, Pk, WD, BS) — ~2 pages
> - **2.2 Neural text segmentation** (SegBot, sentence-embedding methods, transformer-based) — ~2 pages
> - **2.3 Video segmentation & shot-boundary detection** — ~1.5 pages
> - **2.4 Lecture-video segmentation specifically** (AVLectures, PreMind, MOOC segmentation) — ~2 pages
> - **2.5 Multimodal fusion in NLP/video** — ~1.5 pages
> - **2.6 Gap Analysis** — per gap, 1 paragraph: what is missing, which novelty (N1–N7) closes it, which method of ours implements it. ~2 pages
>
> Every paper cited via `\cite{<key>}` where `<key>` matches `thesis/bibliography/references.bib`.

### Verify

```
cd thesis && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Then open `main.pdf` → Chapter 2. Every `[?]` in the text means a broken citation; hunt them down.

---

## ➡️ When done

```
python scripts/mark_done.py T33
python scripts/today.py
```
