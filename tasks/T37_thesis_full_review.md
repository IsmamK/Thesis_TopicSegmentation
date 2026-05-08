# T37 — Full Thesis Review (Citations, Figures, Numbers)

**Phase 9 · Thesis Writing · Estimated time: 1 day · Owner: Sadia + every team member reviews their section**

---

## 🎯 What you are doing
A final pass over the full thesis PDF: every citation resolves, every figure is referenced, every number matches the codebase, every acronym is introduced, voice is consistent throughout.

## ✅ How to know you are done
- `thesis/main.pdf` compiles clean with **zero** warnings.
- A checklist (below) is 100% ticked.

---

## 📝 Steps

### Step 1 — Ask Claude to run an automated check

> Execute T37. Write `scripts/thesis_check.py` that:
> 1. Compiles `thesis/main.tex` and parses the log for undefined references, overfull hboxes, duplicate BibTeX keys.
> 2. Scans all `.tex` files for `\TODO`, `FIXME`, `XXX`, `?.??` placeholders.
> 3. Cross-checks: every table in `main.pdf` has a source `results/.../metrics.csv` (matching row counts).
> 4. Confirms every figure file exists and is >= 100 KB (not a truncated upload).
> 5. Prints a pass/fail report.

### Step 2 — Human checklist

- [ ] Title page has all 5 authors + supervisor + date.
- [ ] Abstract: 250–300 words, no citations, covers all 7 novelties.
- [ ] Acknowledgements page exists.
- [ ] Table of Contents regenerates correctly.
- [ ] List of Figures + List of Tables render.
- [ ] Every chapter begins on a right-hand page (check `\cleardoublepage`).
- [ ] Bibliography sorted alphabetically, all entries complete.
- [ ] No "click here" or broken URL.
- [ ] Page count: 60–100 pages.
- [ ] Font consistent (bibtex keys lowercase, no Courier leak into body).

### Step 3 — Cross-member review

Each author reviews a chapter they did NOT write and flags any claim they cannot verify from the codebase.

### Step 4 — Compile final

```
cd thesis
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Commit the final PDF: `thesis/main.pdf`.

---

## ➡️ When done

```
python scripts/mark_done.py T37
python scripts/today.py
```
