# Automated Segmentation of MOOC Lectures towards Customized Learning

**Authors:** Zhang Quanshi, Li Stan Z., Li Boxin, Zue Anqi
**Year:** 2016
**Venue:** IEEE International Conference on Advanced Learning Technologies (ICALT) 2016
**Citation key:** `zhang2016_mooc`
**Link:** https://ieeexplore.ieee.org/document/7756911/

## BibTeX
```bibtex
@inproceedings{zhang2016_mooc,
  author    = {Zhang, Quanshi and Li, Stan Z. and Li, Boxin and Zue, Anqi},
  title     = {Automated segmentation of {MOOC} lectures towards customized learning},
  booktitle = {Proceedings of the {IEEE} International Conference on Advanced Learning Technologies ({ICALT})},
  pages     = {not reported in abstract},
  year      = {2016}
}
```

## Problem (2 sentences)
MOOC lecture videos are long and monolithic, preventing learners from navigating directly to sub-topics of interest. This paper proposes an automated segmentation approach for MOOC lectures using visual slide-transition detection to break videos into topic-aligned clips suitable for personalised study.

## Method (5 bullets)
- Detects slide transitions by measuring pixel-level or histogram-based visual differences between consecutive frames to identify cuts where a new slide appears.
- Uses optical character recognition (OCR) on detected slide keyframes to extract textual content from each slide region.
- Computes semantic similarity between consecutive slide texts using TF-IDF or keyword overlap to distinguish within-slide scene cuts from genuine topic transitions.
- Clusters semantically similar consecutive slide segments to merge over-segmented outputs and produce coarser topic-level boundaries.
- Evaluates on a collection of MOOC videos from Chinese university online platforms, reporting segmentation precision and recall against manually annotated boundaries.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| MOOC lectures (Chinese university platform) | not reported in abstract | Multiple university subjects |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| Precision / Recall | not reported in abstract | MOOC lectures |

## Limitations (3 bullets, from the paper itself)
- The method depends on slide-based presentation; talking-head or chalkboard lectures without projected slides are not handled.
- OCR quality degrades for videos with low resolution or non-standard fonts, introducing noise into the text similarity step.
- Evaluation is conducted on a proprietary dataset not released publicly, preventing external reproducibility.

## How it relates to our work (1 paragraph)
Zhang et al. 2016 is cited in LECSEG Chapter 2 as an early visual-text approach to MOOC segmentation. It demonstrates that slide transitions are a useful signal, which LECSEG also exploits through its OCR channel. However, LECSEG goes further by combining slides with audio, prosody, and sentence embeddings through a learned reliability-weighted fusion, producing hierarchical outputs rather than flat boundaries from slide transitions alone.

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): Zhang et al. use visual slide detection and OCR text only; LECSEG fuses four modalities and is hierarchical.
- **N2** (reliability-weighted fusion): No learned gating; LECSEG weights modalities by reliability.
- **N3** (two-level output): Single-level output; LECSEG produces chapter + subtopic.
- **N4** (local-LLM refinement): No LLM step; LECSEG uses Llama 3.1 for boundary refinement and auto-titling.
- **N5** (LECSEG-30 dataset): Proprietary dataset; LECSEG releases LECSEG-30 with open annotations.
- **N6** (5-metric eval + CIs): Single metric without CIs; LECSEG uses five metrics with bootstrap CIs.
- **N7** (reproducibility): No public artefact; LECSEG ships `make reproduce`.


