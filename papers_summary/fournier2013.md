# Evaluating Text Segmentation using Boundary Edit Distance (Boundary Similarity)

**Authors:** Chris Fournier
**Year:** 2013
**Venue:** Proceedings of the 51st Annual Meeting of the Association for Computational Linguistics (ACL 2013), Volume 1: Long Papers, pp. 1702–1712, Sofia, Bulgaria
**Citation key:** `fournier2013_boundarysimilarity`
**Link:** https://aclanthology.org/P13-1120/

## BibTeX
```bibtex
@inproceedings{fournier2013_boundarysimilarity,
  author    = {Fournier, Chris},
  title     = {Evaluating Text Segmentation using Boundary Edit Distance},
  booktitle = {Proceedings of the 51st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages     = {1702--1712},
  year      = {2013},
  address   = {Sofia, Bulgaria},
  publisher = {Association for Computational Linguistics},
}
```

## Problem (2 sentences)

Existing segmentation metrics — Pk, WindowDiff, and Segmentation Similarity (S) — can award partial credit for near-miss boundaries but are all biased towards segmentations containing few or tightly clustered boundaries, and S's normalization produces cosmetically high agreement values that overestimate actual performance. This paper proposes Boundary Similarity (B), a metric grounded in boundary edit distance that corrects these biases and supports inter-coder agreement coefficients and a confusion matrix for segmentation.

## Method (5 bullets)

- Define a boundary edit distance adapted from string edit distance: the cost of transforming one segmentation into another using three operations — boundary addition/deletion (full miss, cost 1) and boundary transposition (near miss, cost proportional to displacement distance divided by a tolerance n_t).
- Assign a correctness value to each boundary comparison: exact match = 1.0, transposition at distance d = 1 − (d / n_t), addition or deletion = 0.
- Compute Boundary Similarity B as the mean correctness across all boundary pairs, yielding a score in [0, 1] that is unbiased with respect to the number or clustering of boundaries.
- Derive an inter-coder agreement coefficient by comparing B scores between all annotator pairs, providing a statistically principled measure of labelling reliability.
- Construct a confusion matrix for segmentation (true positive boundaries, false positives, false negatives, near misses) enabling standard information-retrieval metrics such as precision and recall to be computed from B-based counts.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| The Moonstone (novel segmentation with multiple human coders) | Not reported in abstract | Literary / narrative |
| Hypothetical illustrative examples (Coleridge 1816 poetry) | Small synthetic examples | Literary (illustrative only) |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| B vs. S bias demonstration | B gives unbiased ranking of automatic segmenters; S overestimates agreement (qualitative finding) | Moonstone dataset |
| Inter-coder agreement (B-based coefficient) | More accurately reflects coder disagreement than S-based coefficient (exact numbers not reported in abstract) | Moonstone dataset |

## Limitations (3 bullets, from the paper itself)

- The tolerance parameter n_t (maximum transposition distance that still counts as a near miss) must be set by the user, and the metric is sensitive to this choice.
- The paper notes that "future work includes adapting this work to analyse hierarchical segmentations," meaning B is defined only for flat segmentations in this version.
- Evaluated on a limited set of domains (literary texts); generalisability to other genres and modalities is not demonstrated.

## How it relates to our work (1 paragraph)

Boundary Similarity (B) addresses biases in Pk and WindowDiff that are particularly problematic when comparing systems with different granularities — exactly the situation in LECSEG where chapter-level and subtopic-level outputs must be evaluated fairly. B is included in LECSEG's 5-metric suite; the paper's inter-coder agreement coefficient framework also informs how we validate LECSEG-30's hierarchical labels using Cohen's kappa. Fournier's explicit identification of the limitation that B does not yet handle hierarchical segmentations directly motivates one of LECSEG's evaluation contributions (N6).

## Differences from our approach (tied to novelty claims)

- **N1** (hierarchical multimodal): Fournier defines a metric for flat text segmentation; LECSEG is a hierarchical multimodal segmentation pipeline.
- **N2** (reliability-weighted fusion): This is a metric paper with no model or fusion component; LECSEG uses learned reliability-weighted modality gating.
- **N3** (two-level output): B is not defined for hierarchical outputs (the author identifies this as future work); LECSEG produces two-level output and requires adapted evaluation.
- **N4** (local-LLM refinement): Not applicable to a metric paper; LECSEG adds LLM-based boundary refinement and titling.
- **N5** (LECSEG-30 dataset): Evaluated on a literary novel; LECSEG-30 covers lecture recordings with kappa-validated hierarchical labels.
- **N6** (5-metric eval + CIs): Fournier introduces one metric without bootstrap CIs or significance tests; LECSEG unifies B with four other metrics under a framework with bootstrap CIs and Wilcoxon tests.
- **N7** (reproducibility): The segeval Python package implements B, but no end-to-end evaluation pipeline is provided; LECSEG ships a fully reproducible evaluation harness.


