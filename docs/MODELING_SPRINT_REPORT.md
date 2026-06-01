# Modeling Sprint Report

Date: 2026-05-31

This report records the latest modeling work and the defensible thesis position after testing additional improvement paths.

## Current Official Result

Official evaluation setting:

- Ground truth: YouTube chapter boundaries in `data/gt/`
- Videos: 30
- Sentence cap: 800 sentences per video, matching `scripts/run_eval.py`
- Primary metric: Pk and WindowDiff

Current best official method remains:

| Method | Pk | WD | Boundary Similarity | F1@2 |
|---|---:|---:|---:|---:|
| `cross_e5_frac70_minlen11` / `cross_e5large_w9_frac70_minlen11` | 0.3715 | 0.3766 | 0.0314 | 0.0228 |

This is better than the stable BGE divisive baseline:

| Method | Pk | WD |
|---|---:|---:|
| BGE + divisive baseline | 0.3884 | 0.3956 |
| Current best cross-model method | 0.3715 | 0.3766 |

Absolute improvement over the stable baseline:

- Pk: 0.0169
- WD: 0.0190

Relative improvement:

- Pk: about 4.35%
- WD: about 4.80%

## New Experiments Run

### 1. Candidate-Ranker Experiment

New script:

```powershell
.\.venv\Scripts\python.exe scripts\candidate_ranker.py --output results\eval_candidate_ranker.json
```

Purpose:

- Generate many plausible boundary candidates from multiple embedding families.
- Train leave-one-video-out supervised rankers.
- Select top-ranked candidates under minimum-segment constraints.
- Check whether supervised ranking can improve Pk/WD.

Best supervised result:

| Method | Pk | WD | Boundary Similarity | F1@2 |
|---|---:|---:|---:|---:|
| `rank_gb_tol3_frac55_min8_nms2` | 0.4026 | 0.4219 | 0.0618 | 0.1001 |

Conclusion:

- This should not be promoted as the main thesis method.
- It improves direct tolerance F1 over the current best, but Pk/WD become worse.
- For topic segmentation, Pk/WD are the stronger field-standard metrics, so this model is not thesis-best.

Important diagnostic result:

| Oracle | Candidate Recall | Pk | WD | F1@2 |
|---|---:|---:|---:|---:|
| Candidate oracle, tolerance 2 | 0.9681 | 0.0172 | 0.0198 | 0.9806 |
| Candidate oracle, tolerance 5 | 1.0000 | 0.0066 | 0.0082 | 0.9681 |

Interpretation:

- Candidate coverage is excellent.
- The bottleneck is ranking/selecting the correct candidates, not finding candidate locations.
- With only 30 videos, supervised rankers overfit or optimize boundary-level F1 in a way that harms segmentation-window metrics.

### 2. Focused Cross-Model Tuning

New script:

```powershell
.\.venv\Scripts\python.exe scripts\tune_cross_model.py --output results\eval_cross_model_tuning.json
```

Grid searched:

- Primary model: `bge_large`
- Secondary model: `e5large`
- Windows: 7, 9, 11, 13, 15
- Boundary fractions: 0.60, 0.64, 0.66, 0.68, 0.70, 0.72, 0.74, 0.76
- Minimum segment lengths: 8 through 15

Best result:

| Method | Pk | WD | F1@2 |
|---|---:|---:|---:|
| `cross_e5large_w9_frac70_minlen11` | 0.3715 | 0.3766 | 0.0228 |

Conclusion:

- The previous best configuration is stable under a focused local grid.
- There is no honest local tuning gain from nearby parameter changes.
- This is useful defensively: the chosen setting is not arbitrary.

## What This Means for the Thesis

The thesis is stronger if it frames the contribution honestly:

- The project delivers a complete, reproducible lecture topic segmentation pipeline.
- The best method is a conservative cross-embedding segmentation method with minimum-length post-processing.
- The method improves over the stable BGE divisive baseline on Pk/WD.
- The candidate-ranker experiment is valuable as error analysis, not as the final method.
- The main limitation is reliable ranking of semantically plausible candidate boundaries.

Do not claim:

- Pk or WD below 0.30 on the current 30-video YouTube-GT setup.
- Strong supervised performance from the current candidate ranker.
- That LLM refinement is proven to improve official Pk/WD unless a future evaluation shows it.

## Recommended Next Modeling Work

The best next work is not more random local tuning. The best path is:

1. Increase labeled data or create stronger pseudo-labels.
   - The oracle shows candidate coverage is not the issue.
   - More labels would directly improve candidate ranking.

2. Train a sequence-aware ranker.
   - Current candidate ranker scores candidates independently.
   - A better model should rank boundaries jointly, with global constraints.
   - Good options: pairwise ranking loss, CRF-style decoding, or dynamic programming over candidate scores.

3. Add transition-text features.
   - Current features mostly use embedding discontinuity.
   - Add local lexical cues: title-like phrases, discourse markers, recap/intro phrases, slide-change OCR terms.

4. Use stronger long-context embeddings only if GPU time is available.
   - Candidates are already strong, so embeddings alone may not solve ranking.
   - GPU work is still useful for testing modern embedding families consistently across all videos.

5. Evaluate on both YouTube chapters and reviewed subtopics.
   - YouTube chapters are sparse and creator-specific.
   - Subtopic labels may better match the model's semantic boundary behavior.

6. Report statistical confidence.
   - Use bootstrap confidence intervals and Wilcoxon tests for the final comparison.
   - This matters more than chasing tiny fourth-decimal tuning gains.

## Immediate Defensible Thesis Action

Use the current best method as the official model:

```text
cross_e5_frac70_minlen11
```

Use the candidate-ranker experiment as a finding:

```text
Multi-model candidate generation has high oracle recall, but robust boundary ranking remains the main open challenge.
```

This gives the thesis a cleaner and more professional argument than claiming an overfit supervised model as an improvement.
