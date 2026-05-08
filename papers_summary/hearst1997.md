# TextTiling: Segmenting Text into Multi-paragraph Subtopic Passages

**Authors:** Marti A. Hearst
**Year:** 1997
**Venue:** Computational Linguistics, Vol. 23, No. 1, pp. 33–64
**Citation key:** `hearst1997_texttiling`
**Link:** https://aclanthology.org/J97-1003/

## BibTeX
```bibtex
@article{hearst1997_texttiling,
  author  = {Hearst, Marti A.},
  title   = {Text {T}iling: Segmenting Text into Multi-paragraph Subtopic Passages},
  journal = {Computational Linguistics},
  volume  = {23},
  number  = {1},
  pages   = {33--64},
  year    = {1997},
  publisher = {MIT Press},
}
```

## Problem (2 sentences)

Long expository documents contain multiple subtopics, but existing NLP methods lacked principled ways to automatically locate where one subtopic ends and another begins at the multi-paragraph level. TextTiling addresses the problem of partitioning full-length text documents into coherent multi-paragraph passages corresponding to subtopics, without relying on explicit structural markers.

## Method (5 bullets)

- Tokenize text into pseudo-sentences (fixed-size token sequences) and group adjacent sequences into two equal-sized blocks on either side of each candidate gap position.
- Compute a lexical cohesion score at each gap using cosine similarity between the bag-of-words TF vectors of the two flanking blocks (block comparison method); a vocabulary-introduction variant counts new terms introduced in a sliding window.
- Plot similarity scores against gap positions to produce a cohesion profile; compute a depth score at each valley as the sum of the rises to the left and right peaks.
- Identify subtopic boundaries at valley positions whose depth exceeds a threshold derived from the mean minus a multiple of the standard deviation of all depth scores.
- Apply a smoothing step before peak/valley detection to suppress minor fluctuations; final boundaries are placed at valleys surviving the threshold cut.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| Science magazine articles (expository texts, human-annotated) | ~12–13 full-length documents | Popular science / expository prose |
| Human inter-annotator segmentations | Per-document boundary markup by multiple judges | Same articles (used as reference) |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| Precision (TextTiling block method) | 0.43 | Science magazine articles |
| Recall (TextTiling block method) | 0.42 | Science magazine articles |
| Precision (human judges baseline) | 0.66 | Science magazine articles |
| Recall (human judges baseline) | 0.61 | Science magazine articles |

## Limitations (3 bullets, from the paper itself)

- Optimal parameter settings (block size w, smoothing window k) vary from text to text, so no single universal configuration exists.
- The algorithm is designed for long (+1800 words) informative/expository texts with little structural demarcation; performance on shorter or structurally different texts is not established.
- Only the block comparison and vocabulary-introduction scoring variants are formally evaluated; the lexical-chain variant is described but left for future work.

## How it relates to our work (1 paragraph)

TextTiling is the seminal unsupervised lexical-cohesion approach to linear topic segmentation and establishes the core paradigm — sliding-window similarity over bag-of-words representations, valley detection for boundary placement — that nearly all subsequent work (including ours) either extends or benchmarks against. Our LECSEG pipeline targets lecture videos rather than written expository text, but the core motivation — that topic shifts correlate with vocabulary change — carries over. TextTiling therefore serves as a natural text-only baseline against which LECSEG's multimodal gains must be demonstrated.

## Differences from our approach (tied to novelty claims)

- **N1** (hierarchical multimodal): TextTiling is unimodal (plain text) and produces a single flat boundary sequence; LECSEG fuses transcript, slide-visual, and audio modalities in a hierarchical two-level pipeline.
- **N2** (reliability-weighted fusion): TextTiling has no modality fusion mechanism; LECSEG uses learned gating weights that adapt to the reliability of each modality per segment.
- **N3** (two-level output): TextTiling emits one flat sequence of boundaries; LECSEG outputs both coarse chapter-level and fine subtopic-level boundaries.
- **N4** (local-LLM refinement): TextTiling has no post-hoc refinement or automatic titling; LECSEG uses a local LLM to refine boundaries and generate segment titles.
- **N5** (LECSEG-30 dataset): TextTiling was evaluated on ~12 science magazine articles; LECSEG-30 provides 30 kappa-validated lecture recordings with hierarchical ground-truth labels.
- **N6** (5-metric eval + CIs): TextTiling reports precision/recall without confidence intervals or multiple complementary metrics; LECSEG uses a unified 5-metric suite with bootstrap CIs and Wilcoxon tests.
- **N7** (reproducibility): TextTiling predates open reproducibility norms; LECSEG provides a fully reproducible release with code, models, and data.


