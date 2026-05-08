# ✍️ THESIS WRITING GUIDE — Style Rules for Every Author

**This file unifies how all 5 authors write. Read it before writing any Chapter section.**

---

## Voice and tense

- **Voice:** passive or first-person plural ("we"). Never first-person singular ("I").
- **Tense:** simple past for what was done; simple present for what the system does or what a paper claims.
  - "We trained the model on a single GPU." ✓
  - "Whisper produces word-level timestamps." ✓
- **No filler words:** "very", "actually", "basically", "in order to", "it should be noted that…" — strike all.

---

## Every claim is sourced

Three categories of claim, three citation rules:

| Claim type | Example | Source |
|---|---|---|
| Prior work fact | "TextTiling was proposed by Hearst (1997)." | `\cite{hearst1997_texttiling}` |
| Our experimental number | "Our model achieves WD = 0.291." | A row in `results/<exp>/metrics.json` |
| Methodological choice | "We use 5-fold cross-validation at the video level." | `docs/METHODOLOGY.md` and a config in `configs/` |

If you can't source a claim, replace it with something you can.

---

## Numbers in prose

- Round to 3 decimal places: `WD = 0.291`, not `WD = 0.29144`.
- Always bracket with metric and unit: `Pk = 0.247 (±0.012, 95% CI)`.
- For percentages, write `12.6 %` (with non-breaking space if your editor supports it).
- When comparing methods, use **relative** improvement first, **absolute** in parentheses: "12.6 % relative reduction (Δ = 0.043 absolute)".

---

## Tables

- LaTeX `tabular` with `\toprule`, `\midrule`, `\bottomrule` (booktabs).
- Bold the best entry per column.
- Annotate significance with `*`, `**`, `***`.
- Caption above the table; explanation below.

---

## Figures

- Save to `thesis/figures/<chapter>_<short>.pdf` (vector PDFs preferred).
- Caption tells a story; reader should understand without reading the chapter.
- Axes labelled with units. Legend if more than one curve.
- Colour-blind safe palettes (e.g. `viridis`).
- High contrast — must be readable in B&W print.

---

## Acronyms

- Define on first use: "We use sentence-BERT (SBERT)…" then SBERT freely afterwards.
- Don't open a chapter cold with an acronym.

---

## Forbidden words/phrases (in `docs/`, `thesis/`, `paper/`)

The following words flag for review:
- "Claude", "GPT", "AI" (when referring to our use of tools, not when referring to LLM literature in general).
- "prompt" in the sense of "prompt we used".
- "LLM-generated" (about our text).
- "obviously", "clearly", "of course" — they belittle the reader.

`scripts/strip_internal.py` flags these automatically before submission.

---

## Sectioning

- Chapter → Section → Subsection. Don't go deeper than `\subsubsection` unless absolutely needed.
- Each section starts with a 1-sentence summary of what it covers.
- Each section ends with a 1-sentence transition to the next.

---

## The big chapters: how long

| Chapter | Pages |
|---|---|
| 1 — Introduction | 8–10 |
| 2 — Literature Review | 12–15 |
| 3 — Methodology | 18–25 |
| 4 — Results & Analysis | 12–18 |
| 5 — Conclusion | 3–4 |
| 6 — Future Work | 2–3 |
| **Total** | **60–80** |

Plus front matter (~10 pages) and bibliography (~5 pages). Final PDF: 75–95 pages.

---

## Bibliography hygiene

- All entries in `thesis/bibliography/references.bib`.
- BibTeX keys: `<firstauthor><year>_<keyword>` lowercase.
- Every entry has: author, title, year, venue (journal/conference/booktitle).
- For arXiv papers: include `eprint = {2106.XXXXX}` and `archivePrefix = {arXiv}`.

---

## Compile-and-check loop

Always run this before pushing thesis edits:

```
cd thesis
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Then open `main.pdf` and search for `[?]` (broken citations) and `??` (broken refs). Fix them.

---

## Cross-references

Use `\cref{...}` (cleveref package). Examples:
- `\cref{sec:methodology}` → "Section 3"
- `\cref{tab:master}` → "Table 4.2"
- `\cref{fig:pipeline}` → "Figure 3.1"

Never type "Section 3" by hand — it goes stale when you reorder.

---

## Author roles in writing

- **Sadia (lead writer):** drafts every chapter.
- **Each author:** reviews their own contribution sections (e.g., Ismam reviews Methodology fusion section, Shahriar reviews Evaluation, etc.).
- **Sadia:** integrates reviews and finalises.
- **Supervisor:** signs off chapter by chapter.
