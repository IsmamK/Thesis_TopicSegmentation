# 📜 WHAT WE ARE DOING

**Public-facing summary of the project, its motivation, and its phases. Suitable for showing to teachers, the supervisor, and external readers.**

---

## The project in one sentence

We are designing and building an open-source system that automatically splits long lecture videos into hierarchical topic chapters and subtopics, and we evaluate it on a new 30-video corpus we curate and release.

---

## Why it matters

Online education exploded after 2020 and has not slowed. Universities, MOOC platforms, and individual creators publish hundreds of hours of lecture content every day. Most of these videos are unindexed: a learner who wants the 3-minute explanation of a specific concept inside a 90-minute lecture has no efficient way to find it. Manual chapter authoring, where it exists, is laborious and inconsistent.

A reliable lecture-segmentation system improves:

- **Accessibility** — students with attention or sensory disabilities can navigate long content in smaller units.
- **Searchability** — chapter titles become indexable text that improves retrieval.
- **Comprehension** — learners can revisit specific topics rather than re-watching whole lectures.
- **Course authoring** — instructors get a starting structure they can refine, instead of authoring chapters by hand.

Existing approaches are either (a) text-only, (b) closed-source, or (c) flat — they output one level of segmentation. None are simultaneously open, multimodal, and hierarchical.

---

## Our research questions

- **RQ1** — Can a multimodal lecture-segmentation pipeline produce hierarchical (chapter and subtopic) outputs while remaining open-source and reproducible?
- **RQ2** — Does a learned reliability-weighted fusion outperform fixed-weight modality fusion when source quality varies (e.g., chalkboard vs slide-based lectures)?
- **RQ3** — Does a small open local language model match closed-API alternatives for boundary refinement and chapter titling on lecture content?
- **RQ4** — Does explicit modelling of the chapter / subtopic hierarchy improve segmentation quality, measured by a unified hierarchical metric?
- **RQ5** — Are the gains over prior baselines statistically significant under non-parametric testing on a held-out fold?

---

## Contributions

We claim seven contributions, each pinned to one or more modules and one or more experiments:

1. The first open hierarchical multimodal lecture-segmentation pipeline.
2. A reliability-weighted modality-fusion module that adapts per video and per sentence.
3. The first system to output an explicit two-level hierarchy (chapter + subtopic) on lecture video.
4. A boundary-refinement and chapter-titling stage based on a small *open, local* language model — without relying on closed APIs.
5. The LECSEG-30 dataset: 30 videos × 5 domains × dual subtopic annotation, with documented inter-annotator agreement.
6. A unified five-metric evaluation protocol with bootstrap confidence intervals and paired Wilcoxon significance tests.
7. A reproducible artefact: a single command (`make reproduce`) regenerates every numerical claim of the thesis from a fresh clone.

---

## How the project is organised

The work is partitioned into 11 phases and 47 numbered tasks. A short summary:

| Phase | Focus | Tasks |
|---|---|---|
| 1 | Environment setup | T01–T05 |
| 2 | Literature review | T06–T08 |
| 3 | Dataset construction & annotation | T09–T13 |
| 4 | Preprocessing (transcripts, shots, OCR, prosody) | T14–T18 |
| 5 | Multimodal feature extraction | T19–T21 |
| 6 | Baseline implementations | T22–T24 |
| 7 | Novel modules (fusion, boundary predictor, hierarchy, refinement) | T25–T28 |
| 8 | Evaluation, statistics, error analysis | T29–T31 |
| 9 | Thesis writing | T32–T37 |
| 10 | Deliverables (paper, demo, poster, slides, dataset, model release) | T38–T43 |
| 11 | Defense preparation | T44–T47 |

Each task is a short markdown file with:
- a **goal** (one paragraph),
- a **rationale** (why the task is needed),
- a **completion criterion** (how to know you are done),
- step-by-step instructions,
- a concept primer for the concepts the task touches,
- a small troubleshooting table.

Progress is tracked centrally in `progress.yaml`. A dashboard command (`python scripts/today.py`) prints the current state and the next task.

---

## Dataset & ethics

The LECSEG-30 corpus contains 30 publicly available YouTube lecture videos with creator-provided chapter timestamps. We do not redistribute the video files (per YouTube's terms of service); the dataset release contains URLs, metadata, ground-truth chapter and subtopic timestamps, annotation guidelines, and reproduction scripts.

All annotators are project members; annotation guidelines and a sample-of-10 inter-annotator agreement (Cohen's κ at chapter and subtopic levels) are reported in the methodology chapter.

The dataset is published on Zenodo with a CC-BY-4.0 licence. The trained model is published on Hugging Face under a permissive open licence. The full code base is released on GitHub.

---

## Evaluation summary

We compare classical baselines (TextTiling, C99), neural baselines (cosine-drop on sentence embeddings, KMeans segmentation, BERT-SegBot), and our four novel variants on five metrics: Pk, WindowDiff, Boundary Similarity, tolerance-F1, and a hierarchical WindowDiff that we propose. All numbers are reported with bootstrap 95 % confidence intervals (n = 1000 resamples). Pairwise improvements are tested with paired Wilcoxon signed-rank.

---

## Deliverables

- A 60–95 page thesis (`thesis/main.pdf`).
- An 8-page IEEE-style paper (`paper/ieee.pdf`).
- A live web demo (Streamlit, `webapp/`).
- The LECSEG-30 dataset on Zenodo.
- The trained model on Hugging Face.
- An A1 defense poster, slide deck, and Q&A document.

---

## Timeline

The project is organised task-by-task rather than day-by-day, so productive days can advance multiple tasks. The phases above provide rough sequencing; `progress.yaml` records the live state.

---

*This document is a public-facing summary. Internal coordination, project-management notes, and tooling-specific discussion live elsewhere in the repository and are removed before the final submission.*
