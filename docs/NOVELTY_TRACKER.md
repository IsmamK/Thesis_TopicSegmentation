# NOVELTY_TRACKER - Defensible Research Claims

This file records the claims that are safe to defend from the current code,
data, and results. Claims are phrased conservatively: every claim must be
supported by an implemented module and a concrete result or artifact.

## Locked Contributions

| ID | Defensible claim | Evidence | Main files |
|---|---|---|---|
| N1 | Open lecture boundary pipeline with classical, neural, and embedding-based baselines | End-to-end scripts and 30-video results in `results/eval_bge.json` | `scripts/run_eval.py`, `src/lecseg/baselines/`, `src/lecseg/models/` |
| N2 | Reliability-aware multimodal feature framework | Prosody, OCR, shot, visual, and fusion modules are implemented; ablations show these signals need cautious use | `src/lecseg/preprocess/`, `src/lecseg/features/`, `src/lecseg/models/fusion.py` |
| N3 | Two-level chapter/subtopic annotation and hierarchy representation | 30 reviewed hierarchical annotation files; 419 chapters and 904 subtopics | `data/gt_hier/`, `src/lecseg/models/hierarchical.py` |
| N4 | Local LLM refinement and titling component | Ollama-based refiner is implemented; boundary-metric gains must be caveated unless verified in final run | `src/lecseg/refine/llm_refine.py` |
| N5 | LECSEG-30 seed benchmark | 30 public YouTube lectures, 32.52 hours, five domains, 419 chapters, 904 subtopics | `data/manifest.jsonl`, `data/gt/`, `data/gt_hier/` |
| N6 | Unified evaluation suite | Pk, WD, Boundary Similarity, tolerance-F1, H-WD, bootstrap and Wilcoxon utilities | `src/lecseg/metrics.py`, `src/lecseg/eval/stats.py` |
| N7 | Reproducible artifact structure | Dataset, code, tests, results, thesis, and progress log are in one repository | `README.md`, `docs/PROJECT_GUIDE.md`, `Makefile`, `tests/` |

## Current Official Results

Use these numbers unless a newer verified 30-video run replaces them.

| Method | Result file | Pk | WD | BS | F1@2 | Note |
|---|---|---:|---:|---:|---:|---|
| BGE + divisive | `results/eval_bge.json` | 0.3884 | 0.3956 | 0.1292 | 0.0878 | Stable baseline |
| cross_e5_frac70_minlen11 | `results/eval_bgelarge_fine2.json` | 0.3715 | 0.3766 | 0.0314 | 0.0228 | Current best Pk/WD |
| bert_wiki | `results/eval_bert_wiki.json` | 0.4932 | 0.5397 | 0.0411 | 0.0661 | Out-of-domain supervised comparison |

Interpretation:

- The current best improves Pk by 0.0169 absolute over BGE + divisive.
- The current best improves Pk by 0.1176 absolute over the zero-shot
  Wikipedia-trained supervised model.
- Strict tolerance-F1 remains low for the best Pk/WD method; this is a real
  limitation and should be discussed.

## Comparison With TreeSeg

| System | Dataset | Pk | WD | Status |
|---|---|---:|---:|---|
| TreeSeg (Gklezakos et al. 2024) | TinyRec (21 lectures) | 0.367 | — | Prior lecture reference (paper-reported) |
| TreeSeg (Gklezakos et al. 2024) | ICSI meetings | 0.310 | 0.353 | Different domain |
| TreeSeg (Gklezakos et al. 2024) | AMI meetings | 0.355 | — | Different domain |
| LECSEG current best | LECSEG-30 lectures | 0.3715 | 0.3766 | Competitive with TreeSeg on lectures |

Source: arxiv:2407.12028 (LITERATURE_MATRIX.md row verified against abstract).

Safe wording: LECSEG achieves Pk=0.3715 on LECSEG-30 lectures, which is competitive
with TreeSeg's reported Pk=0.367 on TinyRec lectures. The datasets are not directly
comparable (different videos, annotation style, domain mix), so this is indicative
only — a shared-benchmark rerun would be needed for a definitive head-to-head.
Do not claim LECSEG definitively beats TreeSeg without a shared-benchmark rerun.

## Claims To Avoid Or Caveat

- Do not claim Pk/WD below 0.30.
- Do not claim multimodal fusion always improves performance; current ablations
  often show text-only or text-dominant methods winning.
- Do not claim LLM boundary refinement improves metrics unless the final result
  file shows changed boundaries and better scores.
- Do not call the dataset balanced across five domains; the manifest is
  Biology 6, CS 7, Math 4, Philosophy 6, Physics 7.
- Do not cite 31-video `reviewed_only` results as official LECSEG-30 numbers.

## Defense Pitch

LECSEG contributes a reproducible benchmark and engineering artifact for
lecture-video topic segmentation. The strongest scientific contribution is not
that the current method solves segmentation perfectly; it is that the project
documents, measures, and releases a complete pipeline showing which signals work
for lecture boundaries, which fail, and where future supervised candidate
ranking should focus.
