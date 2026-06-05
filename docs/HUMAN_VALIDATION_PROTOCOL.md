# Human Validation Protocol for LECSEG Chapter References

Purpose: measure whether creator-provided YouTube chapters are reasonable reference boundaries for lecture navigation.

## Scope

- Select 8-10 videos from LECSEG-30.
- Include at least 2 Mathematics videos because Math is the current failure domain.
- Use two independent human annotators.
- Annotators must not see the YouTube chapter timestamps during first-pass annotation.

## Annotation Task

Annotators mark chapter-level topic boundaries only. They should mark a boundary when the lecture moves to a new major concept, not every small subtopic.

Required output per annotator:

```json
{
  "video_id": "...",
  "annotator_id": "A",
  "boundaries_sec": [120.0, 450.0, 900.0],
  "notes": "Optional notes on ambiguous transitions"
}
```

## Metrics to Report

| Comparison | Metrics |
|---|---|
| Human A vs Human B | F1@2 sentences, F1@5 sentences, F1@30s, Boundary Similarity |
| Human A vs YouTube | F1@2 sentences, F1@5 sentences, F1@30s, Boundary Similarity |
| Human B vs YouTube | F1@2 sentences, F1@5 sentences, F1@30s, Boundary Similarity |
| LECSEG method vs human average | Pk, WD, F1@5, F1@30s |
| LECSEG method vs YouTube | Existing official metrics |

## Interpretation Rules

- If humans agree strongly with each other and moderately with YouTube, creator chapters are defensible as navigation references.
- If humans disagree with YouTube, the thesis should frame YouTube labels as noisy silver references.
- If the model aligns better with humans than with YouTube in some cases, include those as ground-truth-noise examples.

## Evidence Files to Produce

- `data/human_validation/<video_id>_annotator_a.json`
- `data/human_validation/<video_id>_annotator_b.json`
- `results/human_validation_summary.json`
- `docs/HUMAN_VALIDATION_RESULTS.md`

## Defense Sentence

"YouTube chapters are not assumed to be perfect pedagogical truth. They are reproducible creator-provided navigation references. The planned human validation protocol measures how well those references align with independent annotators."
