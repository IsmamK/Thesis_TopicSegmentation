# Unsupervised Multilingual Topic Segmentation of Video Lectures

**Authors:** Freisinger Miriam, Vu Ngoc Thang, et al.
**Year:** 2023
**Venue:** SLaTE (Speech and Language Technology in Education) Workshop, INTERSPEECH 2023
**Citation key:** `freisinger2023_multilingual`
**Link:** https://www.isca-archive.org/slate_2023/freisinger23_slate.html

## BibTeX
```bibtex
@inproceedings{freisinger2023_multilingual,
  author    = {Freisinger, Miriam and Vu, Ngoc Thang and others},
  title     = {Unsupervised multilingual topic segmentation of video lectures},
  booktitle = {Proceedings of the {SLaTE} Workshop, {INTERSPEECH}},
  year      = {2023}
}
```

## Problem (2 sentences)
Most lecture video segmentation systems are designed for English and require labelled training data, limiting their applicability to multilingual educational content. This paper proposes an unsupervised pipeline that operates on ASR transcripts in multiple languages, combining sentence embeddings with a coherence-based segmentation algorithm.

## Method (5 bullets)
- Transcribes lecture audio with a multilingual ASR system (such as Whisper) to produce transcripts in the source language without manual transcription.
- Encodes sentences using a multilingual sentence embedding model (e.g., LaBSE or multilingual SBERT) to obtain language-agnostic semantic representations.
- Computes cosine similarity between adjacent sentence windows and applies a local-minima detection algorithm to identify coherence drops as topic boundaries.
- Applies the pipeline to lectures in English, Portuguese, and German without any language-specific fine-tuning or annotated data.
- Proposes and evaluates with a Hierarchical WindowDiff variant to capture multi-granularity boundary quality across the three language corpora.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| English lecture corpus | not reported in abstract | Academic lectures |
| Portuguese lecture corpus | not reported in abstract | Academic lectures |
| German lecture corpus | not reported in abstract | Academic lectures |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| WindowDiff | not reported in abstract | Multilingual corpora |
| Hierarchical WindowDiff | not reported in abstract | Multilingual corpora |

## Limitations (3 bullets, from the paper itself)
- The method depends on the quality of the multilingual ASR system; poor transcription degrades segmentation for languages with limited ASR support.
- Unsupervised methods cannot optimise boundary placement for a specific domain; supervised approaches that have access to annotated data typically outperform this approach.
- Evaluation corpora are small and may not represent the diversity of real-world multilingual lecture content.

## How it relates to our work (1 paragraph)
Freisinger et al. 2023 is relevant to LECSEG Chapter 2 as the closest prior work on multilingual lecture segmentation, and because it introduces a Hierarchical WindowDiff metric that is conceptually related to LECSEG's H-WD (N6). LECSEG differs in being a fully supervised, multimodal pipeline focused on English lecture videos with a larger validated benchmark; the multilingual extension is noted as a future direction (Backup novelty B1).

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): Text-only (ASR embeddings); LECSEG fuses four modalities.
- **N2** (reliability-weighted fusion): No learned fusion; single modality.
- **N3** (two-level output): Proposes a hierarchical metric variant but the segmentation itself is single-level; LECSEG jointly trains a two-level decoder.
- **N4** (local-LLM refinement): No LLM step.
- **N5** (LECSEG-30 dataset): Small multilingual corpora; LECSEG-30 is English, 30 videos, publicly released with κ annotation.
- **N6** (5-metric eval + CIs): Evaluates with WindowDiff variants; LECSEG evaluates five metrics with bootstrap CIs and Wilcoxon tests.
- **N7** (reproducibility): Not reported in abstract.


