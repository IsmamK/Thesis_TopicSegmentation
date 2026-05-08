# T38 — IEEE Journal Paper (8 Pages)

**Phase 10 · Deliverables · Estimated time: 2 days · Owner: Sadia + Ismam**

---

## 🎯 What you are doing
Compressing the thesis into an 8-page IEEE-style paper for journal submission. The paper reuses figures and tables from the thesis but with tighter prose.

## ✅ How to know you are done
- `paper/ieee.pdf` compiles at 8 pages exactly (using IEEE template).
- Has: Abstract, Intro, Related Work, Method, Experiments, Results, Conclusion, References.
- BibTeX entries are a subset of `thesis/bibliography/references.bib`.

---

## 📝 Steps

### Ask Claude

> Execute T38. Copy IEEE conference template (e.g., IEEEtran.cls) into `paper/`. Write `paper/ieee.tex` with:
>
> - Abstract (200 words)
> - I. Introduction (0.75 page): problem + our 7-point contribution summary
> - II. Related Work (0.75 page): compress Chapter 2's Gap Analysis
> - III. Method (2.5 pages): the four novel modules + dataset (reuse figures from `thesis/figures/`)
> - IV. Experiments (0.5 page): setup
> - V. Results (2 pages): Master table + H-WD comparison figure + significance
> - VI. Conclusion (0.5 page)
> - References (1 page)
>
> Tight prose, passive voice, no chat-style redundancy. Target: exactly 8 pages including references.

### Verify

```
cd paper && pdflatex ieee.tex && bibtex ieee && pdflatex ieee.tex && pdflatex ieee.tex
wc -l paper/ieee.tex
```

Open `paper/ieee.pdf`. Count pages.

---

## ➡️ When done

```
python scripts/mark_done.py T38
python scripts/today.py
```
