# WHAT WE ARE DOING

This is a public-facing summary of LECSEG. For exact reproducibility details,
official result files, and cleanup rules, use [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md).

## Project In One Sentence

LECSEG builds and evaluates an open, reproducible system that segments long
lecture videos into topic chapters and finer subtopics.

## Why It Matters

Online lecture videos are often long and weakly indexed. Students who need a
specific explanation inside a 60-90 minute recording usually have to scrub
manually. Automatic topic segmentation makes lecture content easier to search,
review, and reuse.

The project is useful for:

- navigation inside long educational videos
- search and retrieval over lecture archives
- semi-automatic chapter drafting for instructors
- research on multimodal educational-video understanding

## Research Questions

- Can an open pipeline segment lecture videos into chapter and subtopic
  boundaries reproducibly?
- Which signals are reliable for lecture segmentation: transcript embeddings,
  visual changes, OCR, prosody, or LLM refinement?
- Does a hierarchy-aware representation provide a better research artifact than
  a flat boundary list?
- How do lecture-specific methods compare with classical, neural, and
  out-of-domain supervised text segmentation baselines?

## Contributions

1. A reproducible lecture-video topic segmentation pipeline.
2. LECSEG-30: 30 public YouTube lectures with chapter and reviewed subtopic
   labels.
3. A hierarchical annotation format for chapters and subtopics.
4. A shared evaluation suite for Pk, WindowDiff, Boundary Similarity,
   tolerance-F1, and hierarchy-aware metrics.
5. Ablations showing that text embeddings dominate the current system, while
   visual/prosody/LLM signals require careful reliability handling.
6. A current best 30-video official result of Pk 0.3715 and WD 0.3766 using a
   conservative cross-model boundary selection variant.

## Current Dataset

| Fact | Value |
|---|---:|
| Videos | 30 |
| Duration | 32.52 hours |
| Chapters | 419 |
| Subtopics | 904 |
| Domains | Biology, CS, Math, Philosophy, Physics |
| IAA | chapter kappa 0.5351; subtopic kappa 0.4257 |

The domain distribution is not perfectly balanced in the current manifest:
Biology 6, CS 7, Math 4, Philosophy 6, Physics 7.

## Current Results

The stable baseline is BGE + divisive segmentation:

| Method | Pk | WD |
|---|---:|---:|
| BGE + divisive | 0.3884 | 0.3956 |

The current best official 30-video YouTube-GT run is:

| Method | Result file | Pk | WD |
|---|---|---:|---:|
| cross_e5_frac70_minlen11 | `results/eval_bgelarge_fine2.json` | 0.3715 | 0.3766 |

The result improves Pk by 0.0169 absolute over the stable baseline. It should
be presented with the limitation that strict boundary F1 remains low.

## Project Organization

| Phase | Focus | Status |
|---|---|---|
| T01-T05 | Setup | Done |
| T06-T08 | Literature and novelty framing | Done; needs final consistency pass |
| T09-T13 | Dataset and annotation | Done |
| T14-T18 | Preprocessing | Done |
| T19-T21 | Features | Done |
| T22-T24 | Baselines | Done |
| T25-T28 | Proposed methods | Done; claims need careful wording |
| T29-T31 | Evaluation and error analysis | Done; official result selection needed |
| T32-T37 | Thesis writing and review | In progress |
| T38-T47 | Paper, demo, release, defense | Not final |

## Deliverables

- thesis source and PDF under `thesis/`
- IEEE-style paper draft under `paper/`
- Streamlit demo under `webapp/`
- dataset metadata and annotations under `data/`
- evaluation results under `results/`
- reproducibility and cleanup guide under `docs/PROJECT_GUIDE.md`

## Public Release Rule

Before any public submission or release, exclude internal coordination files,
Claude worktrees, cookies, vast.ai details, raw videos, and scratch logs. The
release should contain only code, allowed metadata/annotations, reproducible
results, thesis/paper artifacts, and documentation.
