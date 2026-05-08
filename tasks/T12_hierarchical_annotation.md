# T12 — Hierarchical Annotation (Chapters + Subtopics)

**Phase 3 · Dataset · Estimated time: ~1 h per video × 30 = 30 h total, split across 2 annotators · Owner: Fahmida + 1 more annotator**

---

## 🎯 What you are doing
Watching each video and writing **two levels** of boundaries:
1. **Chapter level** (3–10 per video): already have these from T11.
2. **Subtopic level** (2–5 subtopics inside each chapter): **NEW — this is novelty N3**.

You will do this for all 30 videos, and a **second person** will independently annotate **10 of the 30** for inter-annotator agreement (T13).

## 🤔 Why
Our N3 novelty claim is "two-level hierarchical output" — no prior lecture segmentation work releases a dataset with subtopic labels. This is the key dataset contribution.

## ✅ How to know you are done
- `data/gt_hier/<video_id>.json` exists for all 30, with keys `chapters` and `subtopics`.
- `data/gt_hier/annotation_log.md` records who annotated what, when.
- At least 10 videos have been dual-annotated (for T13).

---

## 📝 Steps

### Step 1 — Build the annotation tool

> Execute T12. Write `scripts/annotate.py` — a simple Streamlit app that:
> 1. Lists the 30 videos from `data/manifest.jsonl`.
> 2. For a selected video: shows the YouTube embed, the existing chapter boundaries (from T11), and a text-box per chapter for the annotator to type subtopic timestamps + titles.
> 3. Saves to `data/gt_hier/<video_id>.json` with the format:
>    ```json
>    {
>      "chapters":   [{"start_sec": 0, "title": "..."}, {"start_sec": 630, "title": "..."}],
>      "subtopics": [{"start_sec": 90, "chapter_idx": 0, "title": "..."}, ...]
>    }
>    ```
> 4. Appends a line to `data/gt_hier/annotation_log.md` with annotator id, video id, timestamp, minutes spent.
>
> Ship a README inside `scripts/annotate_README.md` with a walkthrough screenshot and rules.

### Step 2 — Annotation rules (paste this above each annotator's monitor)

**Rules for marking a subtopic boundary:**
- A subtopic boundary is a **clear shift in what is being discussed inside the same chapter**. Examples: from definition to example, from theory to application, from one sub-algorithm to another.
- Minimum subtopic duration: **60 seconds**.
- 2–5 subtopics per chapter (so 10–30 subtopic boundaries per video on average).
- Title must be a short noun phrase (max 8 words). Match the speaker's language.
- If you are unsure, insert the boundary anyway — disagreements feed the kappa study (T13).

### Step 3 — Annotate

Run the tool:

```
streamlit run scripts/annotate.py
```

Annotate videos assigned to you. Target: **1 video per 45 min of video** (so a 1 h lecture takes ~45 min of annotation time).

### Step 4 — Double-annotation for kappa

A second annotator (anyone from the team) picks **10 videos at random** and re-annotates them **without seeing the first annotator's labels**. Save to `data/gt_hier/double/<video_id>.json`.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Annotation** | Labelling data by hand. Here: watching a video and writing where topic-shifts happen. |
| **Subtopic** | A coherent sub-section inside a chapter. "Newton's Laws → Third Law → worked example" = three subtopics in one chapter. |
| **Inter-annotator agreement** | How much two independent humans agree. Computed with Cohen's kappa (κ). Required to prove the task is well-defined. See T13. |

More: [docs/CONCEPTS.md#annotation](../docs/CONCEPTS.md#annotation)

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| Streamlit won't start | `pip install streamlit` then `streamlit run scripts/annotate.py`. |
| Video too long to annotate in one sitting | Tool auto-saves every 30 s. Close the browser, reopen later, it resumes. |
| Two annotators disagree badly | Good — that's exactly what T13 measures. Do not "harmonize" — keep both raw labels. |

---

## ➡️ When done

```
python scripts/mark_done.py T12
python scripts/today.py
```
