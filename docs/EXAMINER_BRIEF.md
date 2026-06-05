# Examiner Brief

This brief states the strongest defensible version of the thesis in one place.
It is intended for supervisors, examiners, reviewers, or future maintainers who
want to understand what LECSEG contributes without reading every experiment log.

## One-Sentence Claim

LECSEG is a reproducible low-resource benchmark and analysis framework for
hierarchical lecture-video topic segmentation, showing what can and cannot be
achieved with 30 manually reviewed lecture videos and lightweight local methods.

## What Is New Here

The novelty is not a large new neural architecture. The contribution is the
combination of:

1. A compact, auditable lecture benchmark with 30 public videos, 32.52 hours,
   419 chapter boundaries, five academic domains, and 904 reviewed subtopics.
2. Explicit hierarchical chapter/subtopic annotation with inter-annotator
   agreement, instead of only flat chapter timestamps.
3. A shared low-resource evaluation protocol covering classical, embedding,
   cross-model, multimodal, selector, oracle, and failed-supervision variants.
4. A statistically checked result boundary that separates supported local
   gains from unsupported state-of-the-art claims.
5. Diagnostic evidence that candidate generation is not the main bottleneck;
   globally selecting the right subset of plausible boundaries is.

This makes LECSEG a benchmark-and-diagnosis contribution rather than a
leaderboard-scaling contribution.

## Main Result

| Method | Pk | WD | BS | F1@2 | Interpretation |
|---|---:|---:|---:|---:|---|
| BGE-divisive baseline | 0.3884 | 0.3956 | 0.1292 | 0.0878 | Stable local baseline |
| Cross-model conservative | 0.3713 | 0.3764 | 0.0362 | 0.0237 | Significant Pk/WD gain over baseline |
| Balanced LOO selector | 0.3588 | 0.3739 | 0.0757 | 0.0893 | Best mean Pk/WD operating point |

The balanced selector significantly improves Pk/WD over the stable baseline.
Its Pk/WD gains over the cross-model method are not significant, but it
significantly improves boundary-hit metrics.

## Low-Resource Positioning

LECSEG is deliberately tiny compared with large chaptering systems:

| Work | Approximate video scale | Scale vs LECSEG-30 |
|---|---:|---:|
| LECSEG | 30 | 1x |
| AVLectures | 2,350+ | 78x |
| Chapter-Gen | 9,631 | 321x |
| Chapter-Llama training subset | 10,000 | 333x |
| MiniSeg / YTSEG | 19,299 | 643x |
| VidChapters-7M | 817,000 | 27,233x |

The safe claim is scale efficiency and reproducibility, not external superiority:
LECSEG shows that a carefully reviewed 30-video lecture benchmark can still
support statistically tested local improvements, detailed ablations, and clear
failure analysis. It does not prove that LECSEG beats high-resource systems on
their benchmarks.

## Why The Result Is Still Useful

The final result is modest, but the study answers a real research question:
what survives when lecture segmentation is forced into a small-data,
low-compute, reproducible setting?

Key findings:

- Embedding-based divisive segmentation is already a strong low-resource
  baseline.
- Cross-model agreement improves segment-window consistency.
- Video-level method selection can improve the mean operating point but is not
  domain-general.
- OCR, shot, and prosody cues are not automatically helpful; their reliability
  depends on lecture style and alignment quality.
- Candidate pools contain much better boundaries than the deployable selector
  chooses, so boundary-level ranking is the next serious research direction.

## Best Defense Wording

Use this:

> This thesis does not claim external state of the art. Its contribution is a
> reproducible low-resource hierarchical lecture-segmentation benchmark and
> diagnostic study. On that benchmark, lightweight cross-model and selector
> methods produce statistically supported local gains over implemented
> baselines, while the oracle and domain analyses show why robust boundary
> selection remains unsolved.

Avoid this:

> Our method performs close to or better than expensive high-resource systems.

That claim requires same-dataset, same-metric evaluation against those systems.

## If More Work Is Added Later

The highest-value future experiment is a same-dataset LLM chaptering baseline.
If a modern LLM baseline is run on the same 30 videos with the same Pk/WD/F1
metrics, then LECSEG can make a much stronger compute-efficiency comparison.
