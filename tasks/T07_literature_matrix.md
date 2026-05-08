# T07 — Build Literature Review Matrix v2

**Phase 2 · Literature Review · Estimated time: 1 hour · Owner: Sadia**

---

## 🎯 What you are doing
Generate an organized table (`docs/LITERATURE_MATRIX.md`) that shows each paper's approach side by side: problem, dataset, method, metrics, limitations, and how it differs from our work.

## 🤔 Why
Chapter 2 cannot be a flat list of paragraphs. A matrix makes it instantly obvious where the gaps in prior work are — which is exactly what the panel wants to see.

## ✅ How to know you are done
- `docs/LITERATURE_MATRIX.md` exists with ≥ 20 rows.
- The "gap column" at the end identifies at least 5 unique gaps.
- Each gap maps to one of our novelty claims N1–N7.

---

## 📝 Steps

### Step 1 — Ask Claude
> Execute T07. Read every file in `papers_summary/`. Build `docs/LITERATURE_MATRIX.md` with columns: Paper (linked to summary), Year, Modality, Method, Dataset, Best Metric, Limitation, Our-novelty-addresses. Sort by year. End with a "Gap Analysis" section listing 5–7 concrete gaps and mapping each to N1–N7.

### Step 2 — Review yourself

Read the matrix. For each row, ask:
- Is the limitation honest (their words, not ours inflating their flaws)?
- Does the "Our-novelty-addresses" column make sense, or is it hand-waving?

If a row feels weak, tell Claude: *"Row for [paper X] has a vague gap. Rewrite it with a specific quantitative or qualitative limitation the paper itself admits."*

---

## ➡️ When done
```
python scripts/mark_done.py T07
python scripts/next.py
```
