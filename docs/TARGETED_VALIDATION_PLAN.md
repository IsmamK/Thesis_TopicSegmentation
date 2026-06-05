# Targeted Validation Plan

This plan replaces a generic "make the dataset bigger" strategy. The current weakness is not raw dataset size; it is Math-domain scarcity, external generalization, and deployment realism.

## Do Not Prioritize

Do not add the 20 already-verified CS-heavy videos as the main upgrade. They would move CS from 7 to 22 videos while Math remains at 4, making the dataset larger but more imbalanced.

## Priority 1: Math-Only Extension

Target:

- Add 8-10 Mathematics lectures with creator chapters.
- Keep this as a chapter-level evaluation extension, not full LECSEG-30 replacement.
- No subtopic annotation is required unless there is enough human time.

Minimum files per new video:

- YouTube URL and metadata in `data/video_list.xlsx`
- transcript
- sentence split
- BGE/E5 embeddings
- creator chapter references
- evaluation output from final methods

Main question:

| Outcome | Interpretation |
|---|---|
| Math improves after adding examples | Prior failure was likely due to too few Math videos |
| Math still fails | Math may need domain-specific features for notation/dense derivation |

## Priority 2: External Holdout

Target:

- 5-10 lecture videos from channels not already represented.
- Do not tune parameters on this set.
- Run only defended final methods.

Report separately from LECSEG-30:

| Dataset | Videos | Method | Pk | WD | F1@2 | Notes |
|---|---:|---|---:|---:|---:|---|
| LECSEG-30 | 30 | Cross-model conservative | 0.3713 | 0.3764 | 0.0237 | Development benchmark |
| External holdout | TBD | Cross-model conservative | TBD | TBD | TBD | No retuning |

## Priority 3: Deployment-Style Metrics

Use `scripts/evaluate_modern_metrics.py` to report:

- F1@1, F1@2, F1@3, F1@5, F1@10
- F1@10s, F1@30s, F1@60s
- boundary count error
- temporal segment overlap

## Defense Sentence

"The best dataset expansion is targeted, not broad. The current known weakness is Math and domain generalization, so the next evaluation should add Math videos and an untuned external holdout rather than adding mostly CS videos."
