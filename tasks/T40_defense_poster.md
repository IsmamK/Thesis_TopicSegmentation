# T40 — Defense Poster (A1)

**Phase 10 · Deliverables · Estimated time: 1 day · Owner: Sadia + Fahmida**

---

## 🎯 What you are doing
A single A1 (594 × 841 mm) portrait poster summarising the thesis. Must be readable from 1 m.

## ✅ How to know you are done
- `poster/poster.pdf` is A1 size, one page.
- Visible from a 1-meter distance (minimum font size 24 pt for body, 60+ pt for title).
- Printed on matte paper (arrange separately).

---

## 📝 Steps

### Ask Claude

> Execute T40. Use `beamerposter` or `tikzposter` LaTeX classes. Layout (top to bottom):
>
> 1. **Header**: title, authors, thesis ID, supervisor, university crest.
> 2. **Top-left**: motivation + problem (1 small figure).
> 3. **Top-right**: our 7 novelties as a vertical icon list.
> 4. **Middle (wide)**: pipeline figure (reuse from thesis).
> 5. **Lower-left**: method at a glance (3–4 bullets).
> 6. **Lower-middle**: headline results table (3 best rows from `master_table.csv`).
> 7. **Lower-right**: a qualitative example figure (one video timeline GT vs pred).
> 8. **Footer**: QR codes to GitHub repo and Zenodo dataset (generate with `qrcode` library).
>
> Body font 24pt. Title 72pt. Use BracU colours (navy + white).

### Verify

Print to A3 first as a draft test. Any text you can't read from arm's length → increase font.

---

## ➡️ When done

```
python scripts/mark_done.py T40
python scripts/today.py
```
