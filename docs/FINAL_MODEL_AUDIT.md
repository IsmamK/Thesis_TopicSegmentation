# Final Model Audit

Date: 2026-06-01

## Current Best Valid Results

There are now two useful "best" results, depending on the primary claim:

| Method | Pk | WD | BS | F1@2 |
|---|---:|---:|---:|---:|
| `cross_e5_frac70_minlen11__align_contains_before` | 0.3713 | 0.3764 | 0.0362 | 0.0237 |
| `method_selector_extra_trainrank_balanced_k80` | 0.3588 | 0.3739 | 0.0757 | 0.0893 |

The alignment-adjusted cross-model method remains the best single global
method. The stable balanced method-selector result is the best mean Pk/WD
operating point and gives much better boundary-hit metrics, but its Pk/WD gains
over the cross-model method are not statistically significant.

## Baseline Comparison

The stable implemented baseline is BGE divisive:

| Method | Pk | WD | BS | F1@2 |
|---|---:|---:|---:|---:|
| BGE divisive | 0.3884 | 0.3956 | 0.1292 | 0.0878 |
| `cross_e5_frac70_minlen11` | 0.3715 | 0.3766 | 0.0314 | 0.0228 |

Absolute improvement:

- Pk: -0.0169
- WD: -0.0190

Relative improvement:

- Pk: 4.35%
- WD: 4.80%

Bootstrap 95% confidence intervals and paired Wilcoxon tests:

| Metric | Baseline 95% CI | Current 95% CI | Delta | p-value |
|---|---:|---:|---:|---:|
| Pk | [0.3602, 0.4160] | [0.3453, 0.3948] | -0.0169 | 0.0073 |
| WD | [0.3680, 0.4240] | [0.3521, 0.3992] | -0.0190 | 0.0002 |
| BS | [0.0835, 0.1808] | [0.0063, 0.0630] | -0.0977 | 0.0019 |
| F1@2 | [0.0596, 0.1193] | [0.0053, 0.0436] | -0.0650 | 0.0081 |

Interpretation for the cross-model conservative method:

- The current method significantly improves Pk and WindowDiff.
- The cross-model method significantly worsens boundary-hit metrics.
- Therefore, the defensible claim for this operating point is improved
  segmentation-window consistency, not better exact boundary detection.
- The later balanced selector partially recovers boundary-hit quality, but its
  Pk/WD gains over the cross-model method are not statistically significant.

## Negative Results From Improvement Sprint

| Experiment | Best method | Pk | WD | BS | F1@2 | Verdict |
|---|---|---:|---:|---:|---:|---|
| DP candidate selector | `dp_agreement_frac70_min11_lw0.08_cb0_max0_cand50` | 0.4096 | 0.4238 | 0.0746 | 0.1067 | Reject |
| Text-transition ranker | `gb_text_tol3_frac35_min8_nms8` | 0.3782 | 0.3866 | 0.0546 | 0.0783 | Reject |
| Low-frac cross-model | `cross_e5large_w9_frac58_minlen11` | 0.3758 | 0.3805 | n/a | 0.0218 | Reject |
| Direct metric search | best global random-weight config | 0.3947 | 0.4083 | 0.0673 | 0.0841 | Reject |
| Direct metric search | leave-one-out selected config | 0.4318 | 0.4389 | 0.0533 | 0.0714 | Reject |
| Guarded ridge selector | best guarded variant | 0.3728 | 0.3777 | 0.0267 | 0.0235 | Reject |
| Direct metric search, seed 11 | best global, 300 samples | 0.3895 | 0.4010 | 0.0565 | 0.0794 | Reject |
| Direct metric search, seed 23 | best global, 300 samples | 0.3915 | 0.4016 | 0.0580 | 0.0750 | Reject |
| Selector pool sweep | k50 ExtraTrees | 0.3634 | 0.3760 | 0.0495 | 0.0608 | Reject |
| Selector pool sweep | k60 ExtraTrees | 0.3693 | 0.3830 | 0.0577 | 0.0693 | Reject |
| Selector pool sweep | k70 ExtraTrees | 0.3695 | 0.3820 | 0.0664 | 0.0772 | Reject |
| Selector pool sweep | k90 ExtraTrees | 0.3678 | 0.3813 | 0.0525 | 0.0642 | Reject |
| Selector pool sweep | k100 ExtraTrees | 0.3663 | 0.3819 | 0.0682 | 0.0837 | Reject |
| Focused cross-model grid | bge-large/e5-large | 0.3738 | 0.3786 | n/a | 0.0245 | Reject |
| Focused cross-model grid | bge-large/e5 | 0.3734 | 0.3790 | n/a | 0.0197 | Reject |
| Focused cross-model grid | e5-large/bge-large | 0.3781 | 0.3858 | n/a | 0.0366 | Reject |
| TreeSeg-style same-dataset | MPNet local embeddings | 0.4320 | 0.4673 | 0.1131 | 0.1733 | Reject for Pk/WD; useful F1 comparator |
| TreeSeg-style same-dataset | E5-large local embeddings | 0.4322 | 0.4654 | 0.1030 | 0.1576 | Reject for Pk/WD; useful F1 comparator |
| TreeSeg-style same-dataset | BGE-large local embeddings | 0.4399 | 0.4780 | 0.1131 | 0.1643 | Reject for Pk/WD; useful F1 comparator |

These experiments do not replace the official method.

## New Portfolio / Method-Selector Results

The method portfolio analysis aggregates existing per-video results and tests
whether the available method family contains complementary wins.

| Experiment | Method | Pk | WD | BS | F1@2 | Interpretation |
|---|---|---:|---:|---:|---:|---|
| Best global portfolio method | `cross_e5_frac70_minlen11__align_contains_before` | 0.3713 | 0.3764 | 0.0362 | 0.0237 | Current best joint Pk/WD |
| Per-video method oracle | oracle over existing methods | 0.2980 | 0.3280 | 0.1366 | 0.1676 | Diagnostic only; not deployable |
| LOO meta-selector | ExtraTrees, balanced train-fold-ranked top-80 methods | 0.3588 | 0.3739 | 0.0757 | 0.0893 | Best valid mean Pk/WD operating point |

The selector result is stronger than the previous best on mean Pk, mean WD, and
F1@2, but it must be described as a leave-one-video-out meta-selection
experiment. It should not be presented as a final production model until the
selector is integrated into a single prediction pipeline and revalidated.

Selector significance analysis in `results/method_selector_significance.json`
shows that the selector's Pk reduction over the current joint-best method is
not statistically significant:

| Comparison | Metric | Delta | p-value | Wins |
|---|---|---:|---:|---:|
| selector vs current joint-best | Pk | -0.0126 | 0.3560 | 9/30 |
| selector vs current joint-best | WD | -0.0025 | 0.9039 | 7/30 |
| selector vs current joint-best | BS | +0.0395 | 0.0076 | 10/30 |
| selector vs current joint-best | F1@2 | +0.0656 | 0.0076 | 10/30 |
| selector vs BGE-divisive baseline | Pk | -0.0296 | 0.0252 | 19/30 |
| selector vs BGE-divisive baseline | WD | -0.0217 | 0.0238 | 23/30 |

Interpretation: use the selector as evidence of complementary method behavior,
boundary-hit recovery, and a significant improvement over the stable baseline,
not as a statistically proven replacement for the cross-model method.

Additional selector diagnostics:

- Operating-point robustness shows k80 is the best tested balanced selector
  pool, with Pk=0.3588 and WD=0.3739; k120 worsens to Pk=0.3716 and WD=0.3852.
- Domain analysis shows selector Pk improves over BGE-divisive in 4/5 domains,
  with Mathematics as the clear failure case.
- Leave-one-domain-out selection drops to Pk=0.4012 and WD=0.4103, worse than
  both BGE-divisive and cross-model conservative results. Do not describe the
  selector as domain-general.

## Main Technical Finding

The candidate oracle from `results/eval_candidate_ranker.json` shows large
headroom:

| Oracle | Recall | Pk | WD | F1@2 |
|---|---:|---:|---:|---:|
| tolerance 2 | 0.9681 | 0.0172 | 0.0198 | 0.9806 |
| tolerance 5 | 1.0000 | 0.0066 | 0.0082 | 0.9681 |

## Submission Readiness

The final machine-checkable claim boundary is recorded in
`docs/SUBMISSION_READINESS.md`.

Current verdict:

- LECSEG is defensible as a reproducible low-resource lecture segmentation
  benchmark/pipeline with statistically supported local Pk/WD gains over
  implemented baselines.
- LECSEG is not defensible as external SOTA or as stronger than the large
  supervised chaptering systems in the related-work comparison.
- The strongest deployable operating point remains the balanced selector
  (`method_selector_extra_trainrank_balanced_k80`), but its Pk/WD gains over
  the cross-model conservative method are not statistically significant.

This means candidate generation is not the main bottleneck. The bottleneck is
choosing the globally correct subset of semantically plausible boundaries.

## Paper Claim Boundary

Use this claim:

> LECSEG improves Pk and WindowDiff over a stable BGE-divisive baseline on a
> 30-video educational lecture dataset, while error analysis shows that robust
> boundary selection remains the main unsolved challenge.

Optional stronger claim, if the method-selector experiment is included:

> A stable balanced leave-one-video-out method selector further reduces Pk to
> 0.3588, WD to 0.3739, and raises F1@2 to 0.0893, showing that LECSEG's method
> portfolio contains complementary boundary evidence. Its Pk/WD gains over the
> joint-best method are not significant, so the main conclusion remains improved
> low-resource segmentation rather than universal state of the art.

Do not claim:

- external state of the art,
- Pk or WD below 0.30,
- superior exact boundary detection,
- a domain-general selector,
- that supervised rankers universally improved the final model.

## Recommended Next Research Direction

The most promising path is not more threshold tuning. The next serious method
should use more supervision or a stronger sequence model:

1. Expand labels or pseudo-labels beyond 30 videos.
2. Train a sequence-aware boundary selector with global constraints.
3. Optimize against Pk/WD while preserving boundary-hit metrics.
4. Add OCR/prosody/slide transition evidence only after verifying alignment
   quality.

The current plateau appears to be caused by sparse and creator-specific
YouTube chapter labels, not by failure to generate candidate boundaries.
