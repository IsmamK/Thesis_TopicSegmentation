# 📥 PAPER ADDITION GUIDE — How to Add a New Paper to Our Literature Review

**Use this whenever a new paper turns up that we should cite.**

---

## The 4-step recipe

### Step 1 — Run the helper

```
python scripts/add_paper.py "<arxiv-url-or-doi-or-title>"
```

This creates `papers_summary/newpaper_TBD.md` from the fixed template.

### Step 2 — Fill in the template

Open the new file. Either fill it in by hand or paste the prompt the script printed into a Claude chat. Required fields (8 sections):

1. Title, authors, year, venue, citation key, link.
2. BibTeX block (with the same citation key).
3. Problem (2 sentences).
4. Method (5 bullets).
5. Datasets table.
6. Metrics & results table.
7. Limitations (3 bullets, in the paper's own words).
8. How it relates to our work + differences vs N1–N7.

Rename the file to `<firstauthor><year>.md` (lowercase) once done.

### Step 3 — Append to bibliography

Copy the BibTeX block from the summary file into `thesis/bibliography/references.bib`.
Make sure the key is unique (no other entry shares the key).

### Step 4 — Regenerate the matrix

```
python scripts/build_literature_matrix.py
```

This pulls every `papers_summary/*.md` and rebuilds `docs/LITERATURE_MATRIX.md`.

If the new paper closes a gap we currently use to defend a novelty, **also update** `docs/NOVELTY_TRACKER.md` — either tighten the gap description or replace the novelty with a backup (B1–B5).

---

## When in doubt

- **Don't know the BibTeX key format?** `<firstauthor><year>_<keyword>` lowercase. Example: `hearst1997_texttiling`.
- **Can't find the PDF?** The arXiv abstract URL is enough — just write `not reported in abstract` in fields you can't fill.
- **Two papers by the same author/year?** Append `_a`, `_b`: `hearst1997_a`, `hearst1997_b`.
- **Withdrawn paper?** Mark `## Status: withdrawn` at the top and exclude from the matrix (`scripts/build_literature_matrix.py` skips files starting with `_`).

---

## Etiquette

- **Don't add a paper just to inflate your bibliography.** Every cited paper must serve at least one chapter section.
- **Cite primary sources.** If a survey cites paper X, cite paper X directly, not the survey.
- **Honesty about limitations.** Use the paper's own words. Don't manufacture weaknesses.
