# Unsupervised Learning and Segmentation of Complex Activities from Video

**Authors:** Fadime Sener, Angela Yao
**Year:** 2018
**Venue:** CVPR 2018 (IEEE/CVF Conference on Computer Vision and Pattern Recognition)
**Citation key:** `sener2018_unsupervised_temporal`
**Link:** https://openaccess.thecvf.com/content_cvpr_2018/html/Sener_Unsupervised_Learning_and_CVPR_2018_paper.html

## BibTeX
```bibtex
@inproceedings{sener2018_unsupervised,
  author    = {Sener, Fadime and Yao, Angela},
  title     = {Unsupervised Learning and Segmentation of Complex Activities from Video},
  booktitle = {Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)},
  year      = {2018},
}
```

## Problem (2 sentences)

Complex instructional activities in video consist of ordered sub-activities, but obtaining frame-level or segment-level annotations is expensive. The paper asks whether such structured activities can be decomposed into their constituent steps purely from visual observations, without any text descriptions or labeled training data.

## Method (5 bullets)
- Adopt an iterative discriminative-generative framework that alternates between two learning phases until convergence.
- Discriminative step: learn a classifier that maps visual frame features to sub-activity pseudo-labels using the current label assignment, capturing the visual appearance of each sub-activity.
- Generative step: model the temporal ordering of sub-activities using a Generalized Mallows Model, which encodes the expected permutation structure of ordered procedural activities.
- Introduce an explicit background model to account for video frames that belong to transitions or irrelevant content, preventing them from corrupting sub-activity representations.
- Iterate the two steps, refining both the visual representations and the temporal model jointly, producing unsupervised segmentation without any ground-truth labels.

## Datasets used
| Dataset | Size | Domain |
|---|---|---|
| Breakfast Actions | ~1,700 videos, 48 activities | Cooking / procedural activities |
| Inria Instructional Videos | ~150 videos, 5 activities | Instructional how-to videos |

## Metrics & headline results
| Metric | Value | Dataset |
|---|---|---|
| Outperforms unsupervised and weakly-supervised SOTA | not reported in abstract | Breakfast Actions |
| Outperforms unsupervised and weakly-supervised SOTA | not reported in abstract | Inria Instructional Videos |

## Limitations (3 bullets, from the paper itself)
- Specific limitation statements are not reported in the abstract; the following are characteristic of the method class.
- The Generalized Mallows Model assumes a fixed canonical ordering of sub-activities, which may not generalise to activities with high intra-class ordering variability.
- The method requires the number of sub-activity classes to be specified in advance, relying on prior knowledge of activity granularity.

## How it relates to our work (1 paragraph)

Sener & Yao demonstrate that temporal structure in procedural video can be recovered without any annotation by combining discriminative visual learning with a generative temporal model. This is conceptually relevant to LECSEG: lectures are also ordered procedural sequences (introduction → development → conclusion) whose structure can be inferred from visual and acoustic cues without dense labelling. Their insight that background modelling is critical to avoid noisy boundary estimates also motivates our reliability-weighted fusion, which down-weights low-confidence modality signals at each candidate boundary.

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): This work operates on a single visual stream only; LECSEG fuses slides, transcript text, and audio in a hierarchical two-level pipeline.
- **N2** (reliability-weighted fusion): No multi-modal fusion; LECSEG uses learned gating to weight modality contributions per segment.
- **N3** (two-level output): Produces flat sub-activity segments; LECSEG outputs chapter-level and subtopic-level boundaries simultaneously.
- **N4** (local-LLM refinement): No LLM post-processing; LECSEG refines boundaries and generates titles using a local LLM.
- **N5** (LECSEG-30 dataset): Evaluated on cooking/instructional video benchmarks; LECSEG-30 is specific to educational lecture video with hierarchical annotations.
- **N6** (5-metric eval + CIs): Specific metrics not reported in abstract; LECSEG reports five metrics with bootstrap confidence intervals.
- **N7** (reproducibility): Code availability not reported in abstract; LECSEG commits to a fully reproducible open release.


