# Claude Execution Playbook — Master Plan

**Removed before submission. This is the full plan Claude and the team use to build LECSEG.**

---

## North star

Build an **open-source, hierarchical, multimodal lecture-video topic-segmentation system** that is:

- **Novel** against 2024-2026 prior work (7 concrete claims N1–N7).
- **Reproducible** — `make reproduce` regenerates every table and figure in the thesis from raw data.
- **Defensible** — every design decision has a paragraph in `docs/METHODOLOGY.md` and a row in the bibliography.

## The 7 novelty claims (summarized)

| ID | One-line claim | Prior-art gap it closes | Implementing module |
|---|---|---|---|
| **N1** | First open hierarchical multimodal lecture-segmentation pipeline | AVLectures (WACV'23) is flat & closed; PreMind is closed-source | `src/lecseg/models/hier_head.py` |
| **N2** | Reliability-weighted modality fusion (learned gating) | Yu 2024 & others fuse with fixed weights | `src/lecseg/models/rw_fusion.py` |
| **N3** | Two-level hierarchical output (chapter + subtopic) | Prior lecture work outputs chapter-only | `src/lecseg/models/hier_output.py` |
| **N4** | Local-LLM boundary refinement + auto-titling | Prior uses closed GPT-4 (unreproducible) | `src/lecseg/refine/llm_refine.py` |
| **N5** | LECSEG-30: 30-video, κ-validated, hierarchical dataset | AVLectures is 86 videos but flat + single-annotator | `data/release/` |
| **N6** | 5-metric evaluation with bootstrap CIs + Wilcoxon | Prior work reports 1–2 metrics without CIs | `src/lecseg/eval/` |
| **N7** | Fully reproducible artifact | Prior work releases code but not data or exact seeds | `Makefile` + `configs/` |

## The 11 phases (see `progress.yaml` for the 47 tasks inside)

1. **Setup** — environment ready to run anything (T01–T05)
2. **Literature Review** — 20 papers summarized, matrix built, novelty locked (T06–T08)
3. **Dataset** — 30 videos curated, downloaded, dual-annotated, κ-validated (T09–T13)
4. **Preprocessing** — transcripts, sentences, shots, OCR, prosody (T14–T18)
5. **Features** — text/visual embeddings aligned to sentence timeline (T19–T21)
6. **Baselines** — classical + neural baselines with same eval protocol (T22–T24)
7. **Novel Method** — 4 modules implementing N1–N4 (T25–T28)
8. **Evaluation** — ablations, CIs, Wilcoxon, error analysis (T29–T31)
9. **Thesis Writing** — 6 chapters, figures, tables, citations (T32–T37)
10. **Deliverables** — paper, demo, poster, slides, dataset release, model release (T38–T43)
11. **Defense Prep** — Turnitin, Q&A, rehearsal, 24-hour checklist (T44–T47)

## How a typical task runs

```
USER:   python scripts/next.py            ← tells them T<NN> is next
USER:   python scripts/claim.py T<NN> <name>
USER:   python scripts/mark_progress.py T<NN> doing
CLAUDE: reads tasks/T<NN>_*.md, executes it
CLAUDE: prints a diff summary
USER:   reviews the diff
USER:   runs the verify commands in the task
USER:   python scripts/mark_done.py T<NN>
SCRIPT: mark_done triggers update_status.py and update_thesis.py
USER:   python scripts/next.py            ← next task
```

## Reproducibility contract

For any experiment (Phase 6 onwards), the output folder must contain:

```
results/YYYYMMDD_HHMM_<exp_name>/
├── config.yaml          # resolved hydra config
├── git_sha.txt          # git SHA of the run
├── env.txt              # pip freeze output
├── metrics.json         # all numbers
├── metrics.csv          # flat table
├── predictions.jsonl    # per-video predictions
├── stderr.log
├── stdout.log
└── figures/*.png
```

## Conventions

- Python: 3.11 only. 3.12+ is not supported.
- Typing: use type hints, `from __future__ import annotations`.
- Logging: `rich.console.Console()` for user-facing, `logging` for internal.
- Random seed: `seed: 42` in every config, set in every script.
- Paths: `pathlib.Path`, never string concatenation.
- Tests: every non-trivial function gets a test in `tests/`.
- Commits: `T<NN>: <verb> <what>` — e.g., `T14: transcribe all 30 videos with Whisper large-v3`.
