# A Framework for Lecture Video Segmentation from Extracted Speech Content

**Authors:** Chand Priya, Ogul Hussein
**Year:** 2021
**Venue:** IEEE International Symposium on Applied Machine Intelligence and Informatics (SAMI) 2021
**Citation key:** `chand2021_framework`
**Link:** https://www.researchgate.net/publication/350294257_A_Framework_for_Lecture_Video_Segmentation_from_Extracted_Speech_Content

## BibTeX
```bibtex
@inproceedings{chand2021_framework,
  author    = {Chand, Priya and Ogul, Hussein},
  title     = {A framework for lecture video segmentation from extracted speech content},
  booktitle = {Proceedings of the {IEEE} International Symposium on Applied Machine Intelligence and Informatics ({SAMI})},
  year      = {2021}
}
```

## Problem (2 sentences)
Lecture videos lack automatic structural markers, making it difficult for students to navigate or for platforms to index content by topic. This paper proposes a speech-based framework that transcribes lecture audio and applies text segmentation to detect topic boundaries in recorded online lectures.

## Method (5 bullets)
- Applies automatic speech recognition (ASR) to convert lecture audio into a transcript, handling pauses and hesitations common in spoken academic language.
- Pre-processes the transcript by removing filler words and applying sentence boundary detection to produce a clean text stream.
- Applies a text segmentation algorithm (based on lexical cohesion, similar to TextTiling) to the transcript to identify positions of probable topic shifts.
- Post-processes the detected boundaries by merging very short segments and aligning boundaries to natural pause points in the audio.
- Evaluates on 37 Coursera lecture videos annotated by the authors, reporting precision, recall, and F1 at the segment level.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| Coursera lectures | 37 videos | Various online courses |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| Precision | 0.69 | Coursera (37 videos) |
| Recall | 0.58 | Coursera (37 videos) |
| F1 | 0.63 | Coursera (37 videos) |

## Limitations (3 bullets, from the paper itself)
- The framework relies solely on speech content; visual signals such as slide transitions and on-screen text are not used.
- ASR errors, especially for technical vocabulary, reduce the quality of the transcript and thus the segmentation accuracy.
- The annotated dataset of 37 videos is not publicly released, limiting reproducibility.

## How it relates to our work (1 paragraph)
Chand & Ogul 2021 is cited in LECSEG Chapter 2 as a recent speech-only segmentation framework. Their approach illustrates the ceiling of speech-text-only methods (F1 ~0.63), motivating LECSEG's multimodal design. LECSEG supplements ASR transcripts with visual embeddings, OCR slide text, and prosody, and learns to weight these modalities adaptively. The low F1 of the speech-only baseline supports LECSEG's hypothesis that multimodal fusion improves accuracy (N2).

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): Speech/text only, single-level; LECSEG is four-modality hierarchical.
- **N2** (reliability-weighted fusion): Single modality, no fusion; LECSEG learns per-modality gates.
- **N3** (two-level output): Flat boundaries; LECSEG outputs chapter + subtopic.
- **N4** (local-LLM refinement): No LLM step.
- **N5** (LECSEG-30 dataset): 37-video unpublished Coursera corpus; LECSEG-30 is open and κ-validated.
- **N6** (5-metric eval + CIs): P/R/F1 without CIs; LECSEG uses five metrics with bootstrap CIs.
- **N7** (reproducibility): No public artefact.


