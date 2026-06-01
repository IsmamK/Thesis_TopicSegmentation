# LECSEG Project Guide

This is the authoritative guide for cleaning, reproducing, and defending the
LECSEG thesis artifact. If another document disagrees with this file, update the
other document or verify the underlying data before using it.

## Official Dataset Facts

Source of truth: `data/manifest.jsonl`, `data/gt/*.json`,
`data/gt_hier/*.json`, and `data/gt_hier/iaa_report.json`.

| Fact | Value |
|---|---:|
| Videos | 30 |
| Total duration | 117,083 seconds / 32.52 hours |
| Chapter boundaries | 419 |
| Reviewed hierarchical files | 30 |
| Subtopics | 904 |
| Mean chapters/video | 13.97 |
| Mean subtopics/video | 30.13 |
| Mean sentences/video | 1,211.7 |

Domain distribution is intentionally recorded as the real manifest state, not a
balanced marketing claim:

| Domain | Videos | Duration (sec) | Chapters |
|---|---:|---:|---:|
| Biology | 6 | 16,999 | 94 |
| CS | 7 | 40,871 | 98 |
| Math | 4 | 12,704 | 55 |
| Philosophy | 6 | 20,277 | 122 |
| Physics | 7 | 26,232 | 50 |

Inter-annotator agreement from `data/gt_hier/iaa_report.json`:

| Level | Kappa | Boundary F1 |
|---|---:|---:|
| Chapter | 0.5351 | 1.0000 |
| Subtopic | 0.4257 | 0.7793 |

## Official Result Policy

The clean official chapter-level benchmark uses:

- Dataset: the 30 videos in `data/manifest.jsonl`
- Ground truth: creator YouTube chapter timestamps in `data/gt/`
- Metrics: Pk, WD, Boundary Similarity, tolerance-F1
- Primary result file for current best: `results/eval_bgelarge_fine2.json`
- Stable baseline file: `results/eval_bge.json`

Current best official 30-video result family:

| Method | File | Pk | WD | BS | F1@2 |
|---|---|---:|---:|---:|---:|
| cross_e5_frac70_minlen11 | `results/eval_bgelarge_fine2.json` | 0.3715 | 0.3766 | 0.0314 | 0.0228 |
| cross_e5_frac70_minlen11__align_contains_before | `results/eval_alignment_sweep.json` | 0.3713 | 0.3764 | 0.0362 | 0.0237 |
| ExtraTrees method selector | `results/method_selector_experiment_trainrank_balanced.json` | 0.3588 | 0.3739 | 0.0757 | 0.0893 |

Stable baseline:

| Method | File | Pk | WD | BS | F1@2 |
|---|---|---:|---:|---:|---:|
| BGE + divisive | `results/eval_bge.json` | 0.3884 | 0.3956 | 0.1292 | 0.0878 |

Important caveat: the best joint Pk/WD cross-model result is conservative and
produces low strict boundary F1. The stable balanced method selector improves
mean Pk/WD and significantly improves F1@2 over the cross-model method, but its
Pk/WD gains over that method are not statistically significant. It does,
however, significantly improve Pk/WD over the stable BGE-divisive baseline. In
the thesis, present Pk/WD as the primary segmentation metrics and discuss
strict F1 as a complementary boundary-hit view.

Do not cite these as official final results without explanation:

- `reviewed_only` runs reporting `n_videos=31`
- scratch logs under `results/_*_run.log`
- experiments where the method name is unclear or not reproducible from one
  command/config

## Reproduction Commands

```powershell
# Environment
.\.venv\Scripts\Activate.ps1

# Tests
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Main evaluation
.\.venv\Scripts\python.exe scripts/run_eval.py --verbose

# IAA
.\.venv\Scripts\python.exe scripts/compute_iaa.py --tolerance 1 --verbose

# Thesis tables/figures
.\.venv\Scripts\python.exe scripts/tables.py results/eval_bge.json
.\.venv\Scripts\python.exe scripts/generate_thesis_result_tables.py
.\.venv\Scripts\python.exe scripts/generate_related_work_comparison.py
.\.venv\Scripts\python.exe scripts/generate_low_resource_positioning.py
.\.venv\Scripts\python.exe scripts/selector_operating_point_analysis.py
.\.venv\Scripts\python.exe scripts/selector_robustness_analysis.py
.\.venv\Scripts\python.exe scripts/domain_performance_analysis.py
.\.venv\Scripts\python.exe scripts/selector_choice_audit.py
.\.venv\Scripts\python.exe scripts/selector_leave_domain_out.py
.\.venv\Scripts\python.exe scripts/generate_defensible_claims.py
.\.venv\Scripts\python.exe scripts/figures.py results/eval_bge.json --output figures/

# Thesis claim validator
.\.venv\Scripts\python.exe scripts/validate_thesis_claims.py

# Final submission-readiness audit
.\.venv\Scripts\python.exe scripts/submission_readiness_audit.py
```

## What Is Defensible

Strong claims:

- LECSEG is an open, reproducible lecture segmentation artifact.
- LECSEG-30 is a real 30-video benchmark with chapter and reviewed subtopic
  labels.
- The project evaluates many baselines under one metric implementation.
- Cross-model conservative boundary selection improves Pk from 0.3884 to
  0.3713 and WD from 0.3956 to 0.3764 on the 30-video YouTube-GT benchmark.
- The stable balanced method-selector experiment reaches Pk=0.3588, WD=0.3739,
  and F1@2=0.0893. Its Pk/WD gain over the joint-best method is not
  statistically significant, but it significantly improves Pk/WD over the
  stable BGE-divisive baseline.
- Generic supervised Wikipedia segmentation transfers poorly to lecture videos
  (`bert_wiki`: Pk 0.4932, WD 0.5397).
- Oracle-k analysis shows segment-count prediction is not the main bottleneck;
  boundary scoring/ranking quality is.

Claims that need careful wording:

- Avoid saying "first" unless the literature review explicitly proves it.
- Do not claim multimodal fusion always helps; visual/prosody signals often
  hurt in current ablations.
- Do not claim LLM refinement improves boundary metrics unless a verified run
  shows changed boundaries.
- Do not claim Pk/WD below 0.30.

## Cleanup Checklist Before Submission

1. Run tests and record the result in `docs/PROGRESS_LOG.md`.
2. Run `scripts/validate_thesis_claims.py` and fix any failed consistency check.
3. Pick exactly one official benchmark table and cite its result file.
4. Remove all thesis `\todo{}` values or convert them into honest limitations.
5. Make domain counts consistent everywhere.
6. Make duration consistent everywhere: 32.52 hours, not 55 hours.
7. Remove stale video IDs that are not in `data/manifest.jsonl`.
8. Keep `internal/`, `.claude/`, cookies, IPs, and scratch logs out of public
   submission/release packages.
9. Rebuild `thesis/main.pdf` after edits.
10. Verify the demo uses a real LECSEG video, not placeholder media.
11. Add a final dated progress-log entry for the cleanup session.

## Recommended Defense Framing

The best defense is not "we solved topic segmentation perfectly." The strongest
framing is:

> Lecture-video segmentation is noisy, label granularity varies, and generic
> text segmentation does not transfer cleanly. LECSEG contributes a reproducible
> benchmark, a clean evaluation suite, and an improved lecture-specific
> segmentation pipeline, while documenting which multimodal and LLM signals help
> or fail.

That framing is honest, technically mature, and defensible under questioning.
