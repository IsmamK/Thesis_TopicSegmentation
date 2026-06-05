# LECSEG - Lecture Video Topic Segmentation

**Group T2520718, BracU CSE400 Final Thesis**  
Temporal segmentation of lecture videos based on content/topic boundaries.

LECSEG is an open research artifact for automatically splitting long lecture
videos into chapter-level and subtopic-level segments. The project includes the
dataset, preprocessing pipeline, segmentation baselines, proposed methods,
evaluation scripts, thesis source, and defense materials.

For a reviewer-facing summary of the final claim boundary, see
[docs/EXAMINER_BRIEF.md](docs/EXAMINER_BRIEF.md).

## Current Authoritative Status

Use [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) as the single cleanup and
handoff guide. It records the current official dataset facts, result files, and
remaining submission checks.

| Item | Current state |
|---|---|
| Dataset | 30 public YouTube lecture videos |
| Duration | 117,083 seconds / 32.52 hours |
| Domains | Biology 6, CS 7, Math 4, Philosophy 6, Physics 7 |
| Chapter labels | 419 creator-provided YouTube chapters |
| Subtopic labels | 904 reviewed hierarchical subtopics |
| IAA | chapter kappa 0.5351, subtopic kappa 0.4257 |
| Stable baseline | BGE + divisive, Pk 0.3884, WD 0.3956 |
| Best valid mean Pk/WD operating point | balanced LOO selector, Pk 0.3588, WD 0.3739 |
| Best single global method | cross-model conservative, Pk 0.3713, WD 0.3764 |

The balanced selector significantly improves Pk/WD over the stable
BGE-divisive baseline. Its Pk/WD gains over the best single global method are
not statistically significant, and leave-domain-out performance is weaker.
The project therefore makes a low-resource, reproducible local-benchmark claim,
not an external state-of-the-art claim.

Recent final-pass artifacts strengthen the defense without changing the
official result:

- Same-dataset TreeSeg-style comparison: `docs/EXPERIMENT_REGISTRY.md` and
  `results/eval_treeseg_same_dataset_*.json`.
- Case-study analysis: `docs/CASE_STUDIES.md`.
- Compute-efficiency table: `docs/COMPUTE_EFFICIENCY.md`.
- Oracle-gap defense note and figure: `docs/DEFENSE_ORACLE_GAP.md`.
- Defense slide deck: `defense/lecseg_defense_slides.pdf`.

## Quick Start

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run tests
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Run final submission gates: registry, claim validation, readiness audit, PDF build
.\.venv\Scripts\python.exe scripts\run_submission_reproduction.py

# Run the main evaluation
.\.venv\Scripts\python.exe scripts/run_eval.py --verbose

# Run the demo
streamlit run scripts/demo.py
```

## Repository Map

| Path | Purpose |
|---|---|
| `src/lecseg/` | Core package: metrics, preprocessing, features, models, refinement |
| `scripts/` | Pipeline, evaluation, annotation, reporting, and helper scripts |
| `data/` | Manifest, transcripts, sentences, GT, embeddings, OCR, shots, prosody |
| `results/` | Experiment outputs and logs |
| `tests/` | Unit and integration tests |
| `docs/` | Project guide, methodology notes, progress log, defense notes |
| `thesis/` | LaTeX thesis source |
| `paper/` | IEEE-style paper draft |
| `webapp/` | Streamlit demo |
| `tasks/` | Original T01-T47 task instructions |
| `internal/` | Internal coordination notes; remove before public release |

## Main Contributions

1. LECSEG-30: a 30-video, 32.52-hour, five-domain lecture benchmark with 419
   chapter boundaries and 904 reviewed subtopic labels.
2. A hierarchical annotation and evaluation setup for chapter/subtopic lecture
   structure, including reported inter-annotator agreement.
3. A reproducible multimodal pipeline covering transcripts, embeddings, OCR,
   shot boundaries, prosody, cross-model selection, and local-LLM refinement.
4. A unified evaluation suite using Pk, WindowDiff, Boundary Similarity,
   tolerance-F1, bootstrap confidence intervals, and paired significance tests.
5. Extensive ablations and diagnostics showing which cues help, which hurt,
   and why candidate-boundary selection remains the main bottleneck.

The intended contribution is benchmark-and-diagnosis quality under severe
data constraints. It is not a claim of external state of the art against
large-scale chaptering systems trained on thousands to hundreds of thousands
of videos.

## Reproducibility Rule

Every result cited in the thesis must point to a concrete file under `results/`
or `data/gt_hier/iaa_report.json`. Do not cite scratch runs, partial runs, or
31-video `reviewed_only` outputs as official 30-video results.

## Release Hygiene

Before submission or public release, remove or exclude:

- `.claude/`, `internal/`, personal notes, and worktrees
- raw videos and unreleasable media
- `data/youtube_cookies.txt`
- vast.ai IPs, SSH details, and temporary logs
- scratch experiment logs that are not part of the final result package

See [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) for the detailed checklist.
