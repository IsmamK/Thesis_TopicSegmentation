# T41 — Defense Slide Deck

**Phase 10 · Deliverables · Estimated time: 1 day · Owner: Ismam + Sadia**

---

## 🎯 What you are doing
A 20-slide beamer deck (each slide ≤ 1 min) for the defense presentation. Structure targets a 20-minute talk + 10-minute Q&A.

## ✅ How to know you are done
- `slides/defense.pdf` is 18–22 slides.
- Every slide ≤ 30 words OR is a figure.
- Numbered and dated.
- A rehearsal timer confirms 18–22 minutes to deliver.

---

## 📝 Steps

### Ask Claude

> Execute T41. Use `beamer` class with a clean theme (e.g., Metropolis).
>
> Slide plan:
> 1. Title slide (team, thesis ID, supervisor, date).
> 2. The problem in 1 picture.
> 3. Motivation (3 numbers: online-ed growth, # lecture hours indexed, user-study navigation pain).
> 4. Research questions.
> 5. Our 7 novelties as a single icon list.
> 6. Related work (3 rows from literature matrix).
> 7. The gap we close.
> 8. LECSEG-30 dataset (domains + κ).
> 9. Pipeline overview figure.
> 10. Reliability-weighted fusion (N2) diagram.
> 11. Two-stage predictor (N1) diagram.
> 12. Hierarchical decoder (N3) diagram.
> 13. LLM refinement (N4) diagram.
> 14. Metrics & evaluation (N6).
> 15. Reproducibility (N7) — make-reproduce demo GIF.
> 16. Master results table — highlight top row.
> 17. Ablation bar chart.
> 18. Significance stars.
> 19. Qualitative example timeline.
> 20. Limitations + future work.
> 21. Contributions recap.
> 22. Thank you + GitHub + dataset QR codes.

### Verify

Rehearse with a timer. Adjust slide count until 20 min ± 2 min.

---

## ➡️ When done

```
python scripts/mark_done.py T41
python scripts/today.py
```
