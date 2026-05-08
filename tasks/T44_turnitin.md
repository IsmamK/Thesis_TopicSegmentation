# T44 — Turnitin Plagiarism + AI Check

**Phase 11 · Defense Prep · Estimated time: 2 h (+ wait) · Owner: Sadia**

---

## 🎯 What you are doing
Submitting the thesis PDF to Turnitin for a **similarity report** + **AI-writing detection**. The target: similarity < 15% and AI-written < 10%.

## ⚠️ Why this matters
Every line written by a generative tool must be reviewed and rewritten in our own voice. Run `python scripts/strip_internal.py --dry-run` BEFORE submitting Turnitin to make sure no AI-specific files accidentally leak into the PDF.

## ✅ How to know you are done
- A Turnitin report exists (PDF).
- Overall similarity ≤ 15%.
- AI-writing detection ≤ 10%.
- Any flagged paragraph has either a citation added or been rewritten.

---

## 📝 Steps

### Step 1 — Strip internal + confirm

```
python scripts/strip_internal.py --dry-run
```

Review flagged lines. Fix any that mention "Claude / AI / prompt".

### Step 2 — Submit thesis/main.pdf to Turnitin (via BracU portal)

Upload `thesis/main.pdf`. Wait ~24 h for the report.

### Step 3 — Review the report

- Similarity matches → check each: is it a correctly cited quote? If no → paraphrase or cite.
- AI-writing: rewrite flagged paragraphs in your own voice.

Re-submit if needed.

---

## ➡️ When done

```
python scripts/mark_done.py T44
python scripts/today.py
```
