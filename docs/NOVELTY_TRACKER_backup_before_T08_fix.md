# 🎯 NOVELTY TRACKER — The 7 Claims We Defend

**Every defensive answer the panel gets points back to a row in this table.**
**Public-facing.**

For each claim N1–N7 we record:

- the **gap** in the prior literature it closes (with citation keys),
- the **module / artefact** that implements it,
- the **experiment** that proves it works,
- the **table or figure** in the thesis that reports the result.

Maintained alongside `docs/LITERATURE_MATRIX.md`. Auto-checked by `python scripts/thesis_check.py`.

---

| ID | Claim | Gap closed (citations) | Module / artefact | Experiment | Proof in thesis |
|---|---|---|---|---|---|
| **N1** | First open hierarchical multimodal lecture-segmentation pipeline | `dss2023_avlectures` is flat & code-only; `wei2024_premind` is closed-source | `src/lecseg/models/boundary_predictor.py` + `hier_output.py` | T26, T27, T29 | Ch.4, Table 4.2 |
| **N2** | Reliability-weighted modality fusion (learned gating) | `yu2024_multimodal` uses fixed concatenation; `karim2024_medvt` does not gate over modalities | `src/lecseg/models/rw_fusion.py` | T25, T29 (row "fixed-weights" vs "RW-fusion") | Ch.4, Table 4.3, Fig. 4.4 |
| **N3** | Two-level hierarchical output (chapter + subtopic) | All prior lecture-segmentation work outputs single-level boundaries | `src/lecseg/models/hier_output.py` | T27, T29 | Ch.4, Table 4.2 (H-WD column) |
| **N4** | Local-LLM boundary refinement + auto-titling | `yu2023_coherence` (EMNLP 2023) and `wei2024_premind` rely on closed GPT-4 — not reproducible | `src/lecseg/refine/llm_refine.py` + Ollama Llama 3.1 | T28, T29 (refine-on/off ablation) | Ch.4, Table 4.5 |
| **N5** | LECSEG-30: a new open κ-validated hierarchical dataset | `dss2023_avlectures` is single-annotator without κ; `tuna2015_classroom` is closed | `data/release/LECSEG-30/` (Zenodo DOI) | T09, T10, T11, T12, T13 | Ch.3, Section 3.2 |
| **N6** | 5-metric unified evaluation with bootstrap CIs and Wilcoxon | Most prior work reports 1–2 metrics without confidence intervals or significance tests | `src/lecseg/eval/metrics.py` + `eval/stats.py` | T22, T30 | Ch.4, Table 4.4 |
| **N7** | Fully reproducible release: `make reproduce` regenerates every table and figure | Most prior work releases code but not data, seeds, or environment | `Makefile`, `configs/`, `results/`, Zenodo, Hugging Face | T29 + final pipeline | Appendix A |

---

## How to maintain this file

When a new paper is added (`scripts/add_paper.py`), check if its claimed contribution overlaps with one of ours. If yes, add it to the **Gap closed** column with a one-line reason why we still differ.

When a module is renamed, update the **Module / artefact** column.

When an experiment table number changes, update the **Proof in thesis** column.

Every row must have **all five fields filled** before T29 is marked done. Partial rows fail `scripts/thesis_check.py`.

---

## Backup novelty pool (in case one collapses)

If literature shows that a claimed novelty is not actually new, replace it with one from this backup pool. Update the table above and `progress.yaml`.

- **B1** — Multilingual capability (Bangla + English mixed lectures).
- **B2** — Real-time inference benchmark (CPU-only laptop).
- **B3** — Slide-aware OCR-conditioned boundary scoring.
- **B4** — Calibrated boundary confidence scores (not just hard predictions).
- **B5** — Active-learning-friendly annotation tool with disagreement highlighting.

---

## Defense-day pitch (memorise this)

> Our seven contributions are: a novel two-stage boundary predictor (N1), the first reliability-weighted modality fusion for lecture video (N2), the first explicit subtopic-level hierarchy (N3), an open-LLM refinement pipeline that matches closed GPT-4 (N4), the LECSEG-30 dataset with κ-validated hierarchical labels (N5), a five-metric evaluation with confidence intervals and significance tests (N6), and a fully reproducible artefact (N7). Every claim is supported by a specific experiment whose configuration is in `configs/` and whose numbers are in `results/`.
