# Defense Slide Outline

This is the recommended defense deck structure. It is designed around the
strongest evidence in the thesis: low-resource benchmark quality, same-dataset
comparisons, and the oracle gap.

## Slide 1 - Title

Hierarchical Multimodal Lecture-Video Topic Segmentation.

Claim: a reproducible low-resource benchmark and diagnostic pipeline for
lecture chapter/subtopic segmentation.

## Slide 2 - Problem

Long lectures are hard to navigate without fine-grained chapters.

Proof object: example timeline with missing/uneven chapters.

## Slide 3 - Gap

Large chaptering systems exist, but low-resource lecture-specific benchmarks
with hierarchy and reproducible diagnostics are rare.

Proof object: scale table showing 30 videos vs 9,631 / 19,299 / 817,000.

## Slide 4 - Dataset

LECSEG-30: 30 videos, 32.52 hours, five domains, 419 chapter boundaries, 904
reviewed subtopics.

Proof object: domain distribution.

## Slide 5 - Pipeline

Transcript, embeddings, OCR, shot, prosody, cross-model selection, selector,
hierarchical output, local LLM/refinement components.

Proof object: pipeline diagram.

## Slide 6 - Main Result

Balanced selector: Pk 0.3588, WD 0.3739, F1@2 0.0893.

Proof object: final-results bar chart.

## Slide 7 - Same-Dataset TreeSeg Comparison

TreeSeg-style local adapters have worse Pk/WD but stronger exact-boundary F1.

Takeaway: LECSEG's conservative method improves segment-window consistency,
while TreeSeg-like splitting creates more exact hits but less coherent segments
under this benchmark.

## Slide 8 - Oracle Gap

Cross-model Pk 0.3713, selector Pk 0.3588, oracle Pk 0.2980.

Takeaway: the hard problem is boundary/method selection, not merely candidate
generation.

## Slide 9 - Case Studies

Show one success, one failure, one Math weakness.

Proof object: `docs/CASE_STUDIES.md`.

## Slide 10 - Efficiency

Local lightweight methods are cheap once embeddings are cached; high-resource
systems require orders of magnitude more data.

Proof object: compute-efficiency table.

## Slide 11 - Limitations

Small corpus, creator-provided chapter labels, Math ASR/notation issues,
selector not domain-general, LLM baseline not fully promoted.

## Slide 12 - Future Work

50-video benchmark, same-dataset LLM baseline, boundary-level verifier,
domain-aware Math processing, reliability-aware multimodal fusion.
