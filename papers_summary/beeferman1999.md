# Statistical Models for Text Segmentation (Pk metric)

**Authors:** Doug Beeferman, Adam Berger, John D. Lafferty
**Year:** 1999
**Venue:** Machine Learning, Vol. 34, pp. 177–210 (Springer)
**Citation key:** `beeferman1999_pk`
**Link:** https://link.springer.com/article/10.1023/A:1007506220214

## BibTeX
```bibtex
@article{beeferman1999_pk,
  author  = {Beeferman, Doug and Berger, Adam and Lafferty, John D.},
  title   = {Statistical Models for Text Segmentation},
  journal = {Machine Learning},
  volume  = {34},
  pages   = {177--210},
  year    = {1999},
  publisher = {Springer},
  doi     = {10.1023/A:1007506220214},
}
```

## Problem (2 sentences)

Automatically partitioning text into coherent topical segments is difficult because segment boundaries do not correspond to simple lexical or syntactic markers, and prior evaluation metrics (precision/recall on exact boundary positions) failed to reward near-miss predictions or account for the probabilistic nature of boundary detection. This paper introduces both a statistical segmentation model and the Pk evaluation metric, which penalises errors in proportion to how far a predicted boundary deviates from the true boundary within a sliding window of size k.

## Method (5 bullets)

- Frame text segmentation as a sequential labelling problem and train exponential (log-linear / maximum entropy) models that assign a probability to each inter-sentence gap being a boundary.
- Extract two classes of features: topicality features, which use adaptive language models to capture broad shifts in word distribution across a window, and cue-word features, which detect domain-specific words that tend to cluster near boundaries.
- Build the model incrementally using a feature-selection procedure that greedily adds the feature providing the greatest improvement in a held-out likelihood criterion.
- Decode the trained model to produce a boundary probability sequence; boundaries are placed where probabilities exceed a tuned threshold.
- Evaluate using the new Pk metric: slide a window of k sentences across the document; for each window, record whether the number of reference boundaries inside the window matches the number of predicted boundaries; Pk is the fraction of windows where they disagree.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| Wall Street Journal articles | Not reported in abstract | News |
| Television broadcast news transcripts | Not reported in abstract | Broadcast news |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| Pk (exponential model vs. decision tree baseline) | Model outperforms baseline (exact numbers not reported in abstract) | WSJ + broadcast news |

## Limitations (3 bullets, from the paper itself)

- The exponential model requires labelled training data with ground-truth boundaries, making it supervised and domain-dependent; performance in new domains without annotation is not addressed.
- Cue-word features may be domain-specific and require re-selection when moving to new text types.
- The Pk metric itself (introduced here) was later shown by Pevzner and Hearst (2002) to penalise false negatives more heavily than false positives and to be sensitive to segment-size distribution — limitations not anticipated in this paper.

## How it relates to our work (1 paragraph)

Beeferman et al. (1999) introduced the Pk metric that became the dominant evaluation standard for topic segmentation throughout the 2000s and is still reported in virtually every segmentation paper, including LECSEG. Understanding Pk's definition — and its known biases, later corrected by WindowDiff and Boundary Similarity — is prerequisite to interpreting all comparative results in our work. The statistical modelling perspective (boundary probability as a learned function of contextual features) also foreshadows the learned-fusion paradigm we adopt, though our modalities extend far beyond text cues.

## Differences from our approach (tied to novelty claims)

- **N1** (hierarchical multimodal): Beeferman et al. use text-only exponential models for flat segmentation; LECSEG is a hierarchical multimodal pipeline.
- **N2** (reliability-weighted fusion): The exponential model fuses textual features within a single modality; LECSEG fuses across modalities with learned reliability gating.
- **N3** (two-level output): The model produces a single flat boundary sequence; LECSEG outputs chapter and subtopic levels.
- **N4** (local-LLM refinement): No boundary refinement or titling is performed; LECSEG applies a local LLM post-hoc.
- **N5** (LECSEG-30 dataset): Evaluated on WSJ and broadcast news; LECSEG-30 covers lecture videos with kappa-validated hierarchical labels.
- **N6** (5-metric eval + CIs): Only Pk is reported, without confidence intervals; LECSEG uses a 5-metric suite with bootstrap CIs and Wilcoxon tests.
- **N7** (reproducibility): No public code or data release; LECSEG provides a fully reproducible release.


