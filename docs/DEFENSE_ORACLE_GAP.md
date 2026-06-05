# Defense Oracle-Gap Brief

Use this as the central defense story: LECSEG is not just a method table; it identifies the next hard problem.

## Core Visual

| Operating point | Pk | WD | F1@2 | Defense meaning |
|---|---:|---:|---:|---|
| Best single global method | 0.3713 | 0.3764 | 0.0237 | Stable low-resource segmentation |
| Balanced selector | 0.3588 | 0.3739 | 0.0893 | Best deployable mean Pk/WD operating point |
| Per-video oracle | 0.2980 | 0.3280 | 0.1676 | Headroom if selection were solved |

## Script

The key finding is that the candidate/method pool already contains much better decisions than the deployable selector can reliably choose. That means the next research problem is not simply adding more candidate boundaries; it is robust boundary selection under low data.

## Low-Resource Scale Line

LECSEG uses 30 videos. Large chaptering systems use from thousands to hundreds of thousands of videos, so LECSEG is a low-resource benchmark and diagnostic artifact, not a direct external-best claim.

## Defense Slide Spine

1. Problem: long lectures need chapter/subtopic navigation.
2. Gap: low-resource lecture segmentation lacks compact, auditable hierarchical benchmarks.
3. Contribution: LECSEG-30, multimodal pipeline, evaluation suite, diagnostics.
4. Result: Pk 0.3588 / WD 0.3739 best deployable operating point.
5. Comparison: TreeSeg-style same-dataset baseline does not beat Pk/WD.
6. Oracle gap: Pk 0.2980 possible inside the method pool.
7. Failure case: Math and selector over-switching.
8. Future: 50-video benchmark, LLM comparison, boundary verifier.
