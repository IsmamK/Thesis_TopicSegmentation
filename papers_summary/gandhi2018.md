# Topic Transition in Educational Videos Using Visually Salient Words

**Authors:** Gandhi Piyush, Biswas Somnath, Deshmukh Omkar D.
**Year:** 2018
**Venue:** Educational Data Mining (EDM) / Xerox Research India (workshop/report, circa 2015–2018)
**Citation key:** `gandhi2018_salient`
**Link:** https://www.semanticscholar.org/paper/Topic-Transition-in-Educational-Videos-Using-Words-Gandhi-Biswas/e821ac70d16e4d0b61b9eba5e8b63be4078c35c3

## BibTeX
```bibtex
@inproceedings{gandhi2018_salient,
  author    = {Gandhi, Piyush and Biswas, Somnath and Deshmukh, Omkar D.},
  title     = {Topic transition in educational videos using visually salient words},
  booktitle = {Proceedings of the International Conference on Educational Data Mining ({EDM})},
  year      = {2018}
}
```

## Problem (2 sentences)
Detecting topic transitions in educational lecture videos is challenging because visual and speech signals are often asynchronous and individually noisy. This paper proposes combining visually salient words—terms visually emphasised by instructors on slides or boards—with ASR transcripts to identify topic boundaries more reliably.

## Method (5 bullets)
- Extracts visually salient words by detecting text rendered prominently on slides, whiteboards, or highlighted by the instructor, using OCR and saliency heuristics (font size, colour, position).
- Constructs a text representation for each short video window by combining OCR-salient words with the ASR transcript, weighting salient words more heavily.
- Trains a Rank-SVM classifier that scores the likelihood of a topic boundary at each window position using the weighted text features.
- Applies a temporal smoothing and peak-detection post-processing step to convert boundary scores into discrete segment boundaries.
- Evaluates on 10 NPTEL lecture videos annotated by domain experts, reporting F-score against ground-truth topic boundaries.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| NPTEL lecture videos | 10 videos | Indian engineering/science lectures |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| F-score | ~0.77 | NPTEL (10 videos) |

## Limitations (3 bullets, from the paper itself)
- The approach is limited to lectures with projected slides or written boards; purely spoken lectures without visual text cues are not addressed.
- The Rank-SVM model requires annotated training examples, making it supervised and data-dependent.
- Evaluation on only 10 videos limits statistical reliability of the reported results.

## How it relates to our work (1 paragraph)
Gandhi et al. is cited in LECSEG Chapter 2 as an example of combining visual saliency with ASR text for lecture segmentation. LECSEG's OCR channel similarly extracts text from slide keyframes; however, LECSEG additionally incorporates sentence-level semantic embeddings, CLIP visual features, and prosody—and learns to weight these modalities via a reliability gate (N2). LECSEG's LECSEG-30 dataset is substantially larger (30 videos across 5 domains) and publicly released with κ-validated annotations (N5).

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): Gandhi et al. produce flat boundaries using OCR saliency + ASR; LECSEG is hierarchical and uses four modalities.
- **N2** (reliability-weighted fusion): Gandhi et al. use a hand-tuned saliency weight; LECSEG learns reliability gates end-to-end.
- **N3** (two-level output): Flat segmentation only; LECSEG adds subtopic level.
- **N4** (local-LLM refinement): No LLM step.
- **N5** (LECSEG-30 dataset): 10-video proprietary NPTEL corpus; LECSEG-30 is 30 videos, open, κ-validated.
- **N6** (5-metric eval + CIs): Single F-score; LECSEG reports five metrics with bootstrap CIs.
- **N7** (reproducibility): No public code or data release.


