# LECSEG Annotation Tool — Quick Start

## Launch

```
streamlit run scripts/annotate.py
```

Opens at http://localhost:8501 in your browser.

---

## Walkthrough

1. **Enter your annotator ID** in the sidebar (e.g. `fahmida`, `rafi`). This is recorded in the log.
2. **Select a video** from the dropdown. The YouTube player loads above.
3. Watch each chapter. For each, type the subtopics you hear in the text box:
   ```
   00:01:30 | Definition of Newton's First Law
   00:04:15 | Worked example — frictionless surface
   00:07:00 | Common misconceptions
   ```
4. Click **Save annotation**. The file is written to `data/gt_hier/<video_id>.json`.

## Rules for subtopic boundaries

| Rule | Detail |
|---|---|
| What counts as a subtopic shift | Clear change in *what* is discussed inside the same chapter (definition → example, theory → application, one sub-algorithm → another) |
| Minimum duration | 60 seconds |
| How many per chapter | 2–5 |
| Title format | Short noun phrase, max 8 words, match the speaker's language |
| If unsure | Insert the boundary anyway — disagreements help T13 |

## Double-annotation (for T13 kappa study)

- Pick any 10 videos you **have not** seen another annotator's labels for.
- Check **"Double-annotation mode"** in the sidebar before saving.
- Output goes to `data/gt_hier/double/<video_id>.json`.

## Output format

```json
{
  "video_id": "TjZBTDzGeGg",
  "annotator": "fahmida",
  "chapters": [
    {"start_sec": 0,   "title": "Introduction"},
    {"start_sec": 630, "title": "Scope of AI"}
  ],
  "subtopics": [
    {"start_sec": 90,  "chapter_idx": 0, "title": "Course logistics"},
    {"start_sec": 210, "chapter_idx": 0, "title": "What is AI?"},
    {"start_sec": 700, "chapter_idx": 1, "title": "Search problems"}
  ]
}
```

## Progress check

The sidebar shows how many of the 30 primary annotations and 10 double annotations are done.
The full audit trail is at `data/gt_hier/annotation_log.md`.
