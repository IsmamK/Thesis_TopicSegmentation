# 🧪 METHODOLOGY — Our Research Plan

**Public-facing. No mention of AI tooling.**

This document describes the research methodology for LECSEG: the dataset, the pipeline, the four novel modules, the evaluation protocol, and the reproducibility guarantees.

---

## 1. Research questions

We address five concrete research questions:

- **RQ1** — Can a multimodal lecture-video segmentation pipeline produce hierarchical (chapter + subtopic) outputs while remaining open-source and reproducible?
- **RQ2** — Does a learned reliability-weighted fusion outperform fixed-weight modality fusion when source quality varies (chalkboard vs slide-based lectures)?
- **RQ3** — Does a small open local language model match closed-API alternatives for boundary refinement and chapter titling on lecture content?
- **RQ4** — Does explicit modelling of the chapter/subtopic hierarchy improve the perceived utility of segmentation, measured by a unified hierarchical metric?
- **RQ5** — Are the gains over prior baselines statistically significant under non-parametric testing on a held-out fold?

---

## 2. Dataset (LECSEG-30)

We construct LECSEG-30, a 30-video corpus spanning five subject domains (Physics, Biology, Computer Science, Mathematics, Philosophy/Humanities). Selection criteria:

- Creator-provided YouTube chapter timestamps (treated as gold-standard chapter boundaries).
- Total duration ≥ 20 hours.
- English audio, ≥ 20 min length, ≥ 3 chapters per video.

Two annotators independently label subtopic boundaries inside each chapter on a randomly selected subset of 10 videos. Inter-annotator agreement is measured by Cohen's κ at chapter and subtopic levels with bootstrap 95 % confidence intervals.

The dataset release contains URLs, metadata, ground-truth chapter and subtopic boundaries, annotation guidelines, and reproduction scripts. Video files themselves are not redistributed (terms of service); the released artefact regenerates the audio/transcript pipeline from URLs.

---

## 3. Pipeline overview

The pipeline transforms each lecture video into a per-sentence multimodal feature matrix, then segments it hierarchically:

1. **Speech-to-text:** Whisper large-v3 produces word-level timestamps.
2. **Sentence splitting:** pysbd merges Whisper segments into clean sentences with start/end seconds.
3. **Shot-boundary detection:** TransNetV2 marks visual cuts.
4. **Slide OCR:** PaddleOCR extracts text from a keyframe per shot.
5. **Prosody:** per-sentence pause length, pitch delta, and rate delta from raw audio.
6. **Text embeddings:** four families compared — MiniLM, MPNet, E5, BGE — providing 384–768-dim vectors per sentence.
7. **Visual embeddings:** CLIP ViT-B/32 per keyframe.
8. **Alignment:** all features resampled to the sentence timeline (every sentence carries text, visual, OCR, prosody features).

---

## 4. Novel modules

### 4.1 Reliability-weighted fusion (N2)

A small per-modality MLP scores how reliable each modality looks at every sentence position. The scores are softmax-normalised across modalities, producing per-step gates that fuse the four feature streams. The gates are learned end-to-end with the boundary loss.

### 4.2 Two-stage boundary predictor (N1)

A bidirectional encoder produces per-sentence boundary scores. A Viterbi decoder enforces global structure: minimum chapter length, maximum chapter length, hard caps on chapter count.

### 4.3 Hierarchical decoder (N3)

A second prediction head produces subtopic boundaries that are constrained to fall strictly between consecutive chapter boundaries. Joint training with a weighted loss (chapter loss × 2, subtopic loss × 1) handles class imbalance.

### 4.4 Local LLM refinement and titling (N4)

Each surviving boundary is tested with a small instruction-tuned open language model (Llama 3.1-8B served locally). Given the 120 s of text on either side of the boundary, the model returns whether the two blocks are about different topics and a 5–8 word title for the next segment. All prompts and responses are cached by hash to guarantee reproducibility and to allow ablations to omit the refinement stage.

---

## 5. Evaluation protocol (N6)

Five metrics are reported jointly:

| Metric | Direction | Source |
|---|---|---|
| Pk | lower is better | Beeferman et al. 1999 |
| WindowDiff | lower is better | Pevzner & Hearst 2002 |
| Boundary Similarity | higher is better | Fournier 2013 |
| Tolerance-F1 (±10 s) | higher is better | this work |
| Hierarchical WindowDiff (H-WD) | lower is better | this work |

Evaluation uses 5-fold cross-validation at the video level. For each method × metric we compute bootstrap (n = 1000) 95 % confidence intervals. The proposed model is compared against every baseline with paired Wilcoxon signed-rank tests; significance is reported at p < 0.05, p < 0.01, and p < 0.001.

---

## 6. Reproducibility (N7)

The repository ships with:

- A frozen `pyproject.toml` pinning every dependency.
- `Makefile` targets `install`, `reproduce`, `thesis`, `paper`, `webapp`.
- `configs/` containing every experiment's resolved Hydra config.
- A pinned random seed (42) propagated through every stochastic component.
- `results/` with one folder per experiment, each containing config, git SHA, environment freeze, raw predictions, and metrics.
- A public dataset DOI (Zenodo) and a public model checkpoint (Hugging Face).

Running `make reproduce` from a fresh clone regenerates every numerical claim in the thesis and paper.

---

## 7. Threats to validity

- **Sample size.** 30 videos limit the power of statistical tests; we partly mitigate with bootstrap CIs and paired tests.
- **English-only.** Generalisation to other languages is left to future work.
- **Creator-provided timestamps.** YouTube chapter labels are assumed to be ground truth; some are imperfect. Detected outliers are documented.
- **Lecture style coverage.** Five domains capture much variability but not all. Field studies (laboratory walkthroughs, hands-on tutorials) are out of scope.
