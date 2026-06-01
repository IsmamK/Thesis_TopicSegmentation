# LECSEG Contributions Reference

Last updated: 2026-06-01.

This is the concise contribution map for thesis writing and defense. It should
stay aligned with [PROJECT_GUIDE.md](PROJECT_GUIDE.md) and
[NOVELTY_TRACKER.md](NOVELTY_TRACKER.md).

## Contribution Summary

| ID | Contribution | Status | Evidence |
|---|---|---|---|
| C1 | Reproducible lecture segmentation pipeline | Implemented | `scripts/pipeline.py`, `scripts/run_eval.py`, `src/lecseg/` |
| C2 | LECSEG-30 benchmark | Implemented | 30 videos, 32.52 h, 419 chapters, 904 subtopics |
| C3 | Hierarchical chapter/subtopic annotation format | Implemented | `data/gt_hier/`, `scripts/annotate.py`, `scripts/compute_iaa.py` |
| C4 | Unified metrics and evaluation | Implemented | `src/lecseg/metrics.py`, `src/lecseg/eval/stats.py` |
| C5 | Conservative cross-model boundary selection | Implemented in experiment code | `results/eval_bgelarge_fine2.json`, Pk 0.3715, WD 0.3766 |
| C6 | Negative/diagnostic findings | Implemented | Oracle-k, multimodal ablations, bert-wiki transfer result |
| C7 | Method-portfolio and meta-selection analysis | Implemented | `scripts/method_portfolio_analysis.py`, `scripts/method_selector_experiment.py` |

## Dataset Evidence

| Quantity | Value |
|---|---:|
| Videos | 30 |
| Duration | 32.52 hours |
| Chapters | 419 |
| Subtopics | 904 |
| Mean chapters/video | 13.97 |
| Mean subtopics/video | 30.13 |
| Chapter kappa | 0.5351 |
| Subtopic kappa | 0.4257 |

## Result Evidence

| Method | File | Pk | WD | F1@2 | Role |
|---|---|---:|---:|---:|---|
| TextTiling | `results/eval_bge.json` | 0.6053 | 0.8978 | 0.1390 | Classical baseline |
| C99 | `results/eval_bge.json` | 0.4219 | 0.4494 | 0.0290 | Classical baseline |
| CosineSeg | `results/eval_bge.json` | 0.4902 | 0.5392 | 0.0855 | Neural/embedding baseline |
| KMeansSeg | `results/eval_bge.json` | 0.6172 | 0.9986 | 0.0460 | Degenerate baseline |
| BertSeg | `results/eval_bge.json` | 0.4891 | 0.5403 | 0.0910 | Neural baseline |
| BGE + divisive | `results/eval_bge.json` | 0.3884 | 0.3956 | 0.0878 | Stable strong baseline |
| cross_e5_frac70_minlen11 | `results/eval_bgelarge_fine2.json` | 0.3715 | 0.3766 | 0.0228 | Current best Pk/WD |
| cross_e5_frac70_minlen11__align_contains_before | `results/eval_alignment_sweep.json` | 0.3713 | 0.3764 | 0.0237 | Best joint Pk/WD after alignment audit |
| ExtraTrees method selector | `results/method_selector_experiment_trainrank_balanced.json` | 0.3588 | 0.3739 | 0.0893 | Stable balanced selector; significant Pk/WD gain vs BGE baseline |
| bert-wiki zero-shot | `results/eval_bert_wiki.json` | 0.4932 | 0.5397 | 0.0661 | Out-of-domain supervised comparison |

## What To Emphasize

- The dataset and evaluation package are strong.
- The current best method improves Pk/WD over the stable BGE-divisive baseline.
- The stable balanced method-selector experiment improves mean Pk/WD further
  and recovers boundary-hit quality. Its Pk/WD gains over the joint-best method
  are not significant; its F1@2 and Boundary Similarity gains over that method
  are significant, and its Pk/WD gains over the BGE-divisive baseline are
  significant.
- Out-of-domain supervised segmentation transfers poorly to lectures.
- Segment-count selection is not the main bottleneck; boundary scoring/ranking
  is the next research direction.
- Strict F1 is low for the best Pk/WD method, so exact boundary matching should
  be discussed honestly.

## What To Avoid

- Do not claim international state-of-the-art.
- Do not claim sub-0.30 Pk/WD.
- Do not claim that every modality improves the result.
- Do not cite stale values: 55 hours, 329 chapters, balanced 5x6 domains.
- Do not cite `reviewed_only` 31-video runs as official LECSEG-30 results.

## Suggested Thesis Claim

> LECSEG provides a reproducible lecture-video segmentation benchmark and
> pipeline. On the 30-video chapter task, conservative cross-model boundary
> selection improves Pk from 0.3884 to 0.3713 over a strong BGE-divisive
> baseline. A stable balanced leave-one-video-out method selector further
> reduces Pk to 0.3588 and WD to 0.3739, with significant Pk/WD gains over the
> BGE baseline and significantly higher F1@2 than the cross-model method, while
> the full artifact exposes the remaining difficulty of exact lecture boundary
> placement.

This claim is accurate, defendable, and supported by the current repository.
