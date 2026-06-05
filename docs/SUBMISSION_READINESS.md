# Submission Readiness Audit

Generated: 2026-06-05 06:56:06
Status: **PASS**

## Verdict

Ready for a defensible thesis submission claim boundary: LECSEG is a reproducible low-resource lecture segmentation benchmark and pipeline with statistically supported local Pk/WD gains over implemented baselines, but it is not an external SOTA system.

## Key Results

| Method | Pk | WD | BS | F1@2 |
|---|---:|---:|---:|---:|
| BGE-divisive baseline | 0.3884 | 0.3956 | 0.1292 | 0.0878 |
| Cross-model conservative | 0.3713 | 0.3764 | 0.0362 | 0.0237 |
| Balanced LOO selector | 0.3588 | 0.3739 | 0.0757 | 0.0893 |

## Significance Summary

- Balanced selector vs BGE baseline: Pk and WD are statistically significant local improvements.
- Balanced selector vs cross-model conservative: Pk/WD differences are not statistically significant.
- Balanced selector vs cross-model conservative: BS and F1@2 improve significantly.

## What Can Be Claimed

- LECSEG is a reproducible lecture segmentation benchmark/pipeline with a 30-video, 32.52-hour YouTube lecture benchmark.
- The best deployable local result is the balanced leave-one-out selector: Pk=0.3588, WD=0.3739, BS=0.0757, F1@2=0.0893.
- The thesis contains external related-work and low-resource comparisons against large chaptering systems.
- Oracle evidence shows candidate selection/ranking is the main remaining bottleneck.

## What Must Not Be Claimed

- Do not claim external state of the art.
- Do not claim LECSEG beats MiniSeg/YTSEG, VidChapters-7M, Chapter-Gen, Chapter-Llama, or other large supervised systems on their own benchmarks.
- Do not claim the selector is domain-general; leave-domain-out evaluation is weaker than the local benchmark.

## Checks

- Claim validator: pass (113 passed, 0 failed).
- Audit checks: 43 passed, 0 failed.

No submission-readiness failures were found by this audit.

Residual risk: this does not prove external SOTA; it proves that the current thesis artifacts support the safer defensible claim boundary.
