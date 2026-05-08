# T45 — Defense Q&A Preparation Document

**Phase 11 · Defense Prep · Estimated time: 1 day · Owner: everyone**

---

## 🎯 What you are doing
Building `docs/DEFENSE_QA.md` — 50+ anticipated panel questions with bullet-point answers + thesis-chapter references. You will study this in the 48 hours before the defense.

## ✅ How to know you are done
- `docs/DEFENSE_QA.md` has ≥ 50 Q&A pairs across 6 categories.
- Each answer references a specific chapter/section/table of the thesis.
- Each of the 5 team members can answer 10 questions from memory.

---

## 📝 Steps

### Ask Claude

> Execute T45. Read the whole thesis. Produce `docs/DEFENSE_QA.md` with 50+ questions across these 6 categories. Each Q has a bulleted answer + exact chapter/table reference.
>
> **Categories:**
> 1. **Motivation & novelty** (10 Qs) — "What's actually new?" "Why not use GPT-4?" "Why 30 videos and not 300?"
> 2. **Dataset** (8 Qs) — "How do you handle YouTube ToS?" "What is κ and why is it 0.XX?"
> 3. **Methods** (12 Qs) — one Q per novel module. "How is reliability computed?" "Why Viterbi not CRF?"
> 4. **Experiments & statistics** (10 Qs) — "Why 5-fold, not 10-fold?" "Why Wilcoxon not t-test?"
> 5. **Limitations & threats to validity** (6 Qs) — "How small is 30?" "Does LLM hallucinate titles?"
> 6. **Implementation & reproducibility** (4 Qs) — "How much GPU memory?" "What if my Ollama crashes?"

### Step 2 — Practice

Each team member picks 10 Qs from their area of responsibility. Practise answering aloud in ≤ 90 s each. Record yourselves.

---

## ➡️ When done

```
python scripts/mark_done.py T45
python scripts/today.py
```
