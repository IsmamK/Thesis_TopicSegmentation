# A Critique and Improvement of an Evaluation Metric for Text Segmentation (WindowDiff)

**Authors:** Lev Pevzner, Marti A. Hearst
**Year:** 2002
**Venue:** Computational Linguistics, Vol. 28, No. 1, pp. 19–36
**Citation key:** `pevzner2002_windowdiff`
**Link:** https://aclanthology.org/J02-1002/

## BibTeX
```bibtex
@article{pevzner2002_windowdiff,
  author  = {Pevzner, Lev and Hearst, Marti A.},
  title   = {A Critique and Improvement of an Evaluation Metric for Text Segmentation},
  journal = {Computational Linguistics},
  volume  = {28},
  number  = {1},
  pages   = {19--36},
  year    = {2002},
  publisher = {MIT Press},
  doi     = {10.1162/089120102317341756},
}
```

## Problem (2 sentences)

The Pk metric (Beeferman et al., 1999) had become the standard for evaluating text segmentation, but a theoretical analysis reveals that it penalises false negatives more heavily than false positives, assigns the same penalty to near misses as to distant errors, and is sensitive to variation in the reference segment-size distribution. This paper identifies these failure modes and proposes WindowDiff, a simple modification that resolves all three problems.

## Method (5 bullets)

- Prove analytically that Pk penalises missed boundaries (false negatives) at roughly twice the rate of spurious boundaries (false positives) because a missed boundary affects k windows while a false alarm affects fewer on average.
- Show that Pk gives equal penalty to a boundary placed one sentence away from the correct position and one placed at the opposite end of the document, failing to reward near-miss predictions.
- Demonstrate that Pk scores vary with the reference segment-length distribution even when the algorithm's behaviour is held constant, making cross-corpus comparisons unreliable.
- Propose WindowDiff: for each window position i, compute |b_ref(i,i+k) − b_hyp(i,i+k)| where b(·) counts the number of boundaries inside the window; WindowDiff is the mean of these absolute differences over all windows, penalising any mismatch in boundary count symmetrically.
- Empirically validate that WindowDiff corrects all three identified biases on the Choi synthetic dataset and on a medical abstracts corpus.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| Choi synthetic dataset (Brown Corpus concatenations) | 700 documents | General / synthetic |
| Medical abstracts corpus | Not reported in abstract | Biomedical |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| WindowDiff improvement over Pk on near-miss cases | 5–15% lower error rate (approximate, from paper) | Choi synthetic dataset |
| WindowDiff false-positive / false-negative symmetry | Symmetric (by construction) | Theoretical proof |

## Limitations (3 bullets, from the paper itself)

- The window size k must still be chosen (typically set to half the mean reference segment length), and the choice affects the score, leaving a degree of arbitrariness.
- WindowDiff still requires careful calibration for documents with highly variable segment-length distributions.
- Both Pk and WindowDiff count boundary events inside a window without regard for exactly where inside the window those boundaries fall, so they still cannot distinguish errors of different spatial magnitudes beyond the window scale.

## How it relates to our work (1 paragraph)

WindowDiff is one of the two most widely reported segmentation metrics (alongside Pk) and is included in LECSEG's 5-metric evaluation suite. The paper's theoretical critique of Pk directly motivates why our evaluation uses multiple complementary metrics rather than relying on any single measure: each metric captures a different failure mode, and reporting all five (Pk, WindowDiff, Boundary Similarity, F1, and a coverage metric) with bootstrap confidence intervals gives a more complete and honest picture of system performance.

## Differences from our approach (tied to novelty claims)

- **N1** (hierarchical multimodal): Pevzner and Hearst address evaluation methodology for flat text segmentation; LECSEG is a hierarchical multimodal segmentation system.
- **N2** (reliability-weighted fusion): This paper proposes a metric, not a segmentation model; no fusion is involved.
- **N3** (two-level output): WindowDiff is defined for flat segmentations; LECSEG's evaluation must handle two-level hierarchical outputs.
- **N4** (local-LLM refinement): Not applicable to a metric paper; LECSEG adds LLM-based refinement and titling as a pipeline stage.
- **N5** (LECSEG-30 dataset): Evaluated on synthetic and medical-abstract data; LECSEG-30 provides lecture recordings with kappa-validated hierarchical labels.
- **N6** (5-metric eval + CIs): This paper introduces one metric; LECSEG unifies five metrics under a common evaluation framework with bootstrap CIs and Wilcoxon tests.
- **N7** (reproducibility): Metric implementation is straightforward but no unified evaluation toolkit was released; LECSEG ships a reproducible evaluation harness.


