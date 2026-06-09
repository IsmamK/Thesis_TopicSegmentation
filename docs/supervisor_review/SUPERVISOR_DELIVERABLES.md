# LecSeg — Supervisor Review Package
**Student:** Ismam Khan | **Project:** T2520718 — Pre-Thesis 2  
**Date:** 2026-06-09 | **GitHub:** https://github.com/IsmamK/Thesis_TopicSegmentation

---

## 1. Key Deliverables (What to Share)

| Deliverable | File / Location | Status |
|---|---|---|
| Final thesis PDF | `thesis/main.pdf` (78 pages) | ✅ Ready |
| Defense slides v4 | `thesis/LECSEG_Defense_Slides_v4.pptx` (26 slides) | ✅ Ready |
| Supervisor brief (1-page) | `docs/supervisor_brief.pdf` | ✅ Ready |
| GitHub repository | https://github.com/IsmamK/Thesis_TopicSegmentation | ✅ Public |
| External validation charts | `thesis/figures/external_eval_per_video.png` + `_per_domain.png` | ✅ Ready |
| Eval results JSON | `results/external_eval.json` | ✅ Ready |

> **Note on items requested by supervisor that require external accounts:**
> - **Google Spreadsheet self-scoring** — created below in Section 4
> - **Overleaf editable link** — requires uploading the LaTeX source; see Section 5
> - **Turnitin submission** — requires supervisor's class ID and enrollment key; see Section 6
> - **Folder of all files** — this repository IS the folder; see Section 7

---

## 2. Checklist Compliance (Supervisor's Checklist)

### Abstract ✅
- Follows Nature abstract structure: background, gap, approach, results, impact
- Includes concrete quantitative results: Pk=0.371 (cross-model), Pk=0.389 external
- No undefined abbreviations in abstract

### Background & Motivation ✅
- Chapter 1 (Introduction): 4 sections — Motivation, Problem statement, Positioning, Contributions
- Cites 8 relevant prior works in motivation section
- Literature review summary table (Table 2.1) included in Chapter 2

### Aim & Research Questions ✅
- 5 research questions explicitly stated (RQ1–RQ5, Section 1.4)
- RQs cover: embedding strategies, method selector, hierarchy, auxiliary signals, statistical significance
- All RQs answered in Chapter 5 Section 5.2

### Dataset & External Validation ✅
- LecSeg-30: 30 videos, 5 domains, 32.52 hours, 419 chapters, 904 human annotations
- External validation (Section 4.11): 10 videos across CS, Math, Physics, Biology, Philosophy
  - BGE-divisive mean Pk=0.389 external vs 0.388 LecSeg-30 (Δ=0.001) — consistent
  - Cross-model mean Pk=0.421 external vs 0.371 LecSeg-30 — some degradation
- EDA: domain distribution, chapter density, sentence count distributions all reported

### Methodology ✅
- Full pipeline documented (Chapter 3, Figure 3.1)
- Multiple methods compared: 7 baselines + 4 integrated components + method selector
- Leave-one-video-out cross-validation used for selector training
- Bootstrap 95% CIs + Wilcoxon+Holm significance testing (Section 3.4.4)
- Ethical considerations: Section 3.2.4 (construct scope and limitations)
- FAIR principles: public GitHub repo, reproducible scripts, open data sources

### Findings / Results ✅
- Chapter 4: quantitative results with Pk/WD/BS/F1 metrics
- Two central findings: oracle gap (Section 4.8) and granularity mismatch (Section 4.6)
- Visualizations: Fig 4.1 (main results), Fig 4.2 (domain analysis), Fig 4.3–4.4 (external)
- All figures referenced in text

### Result Validation ✅
- Primary: Pk, WindowDiff (lower=better)
- Secondary diagnostics: Boundary Similarity (BS), tolerance-F1, Hierarchical WD
- Bootstrap 95% CIs reported for all metrics
- Wilcoxon tests with Holm correction for pairwise comparisons
- Leave-domain-out generalization test (Pk=0.4012)
- External validation on 10 unseen videos (Section 4.11)

### Conclusion ✅
- Chapter 5: clear conclusions tied to each RQ
- Practical implications for future supervised boundary rankers
- Threats to validity section (Section 5.5) is thorough

### Future Work ✅
- Chapter 6: 11 concrete future directions with rationale
- Most important: supervised boundary ranker (closes oracle gap)

### References ✅
- plainnat citation style (standard academic)
- 34 references spanning 1994–2025
- All cited works discussed in text
- Includes classic papers (TextTiling 1994, C99 2000) and recent (2023–2025)

---

## 3. Rubric Compliance (CO Mapping)

| CO | Description | Evidence in Thesis | Marks |
|---|---|---|---|
| CO1 | Formulate complex computing problem | Ch1: Background, Problem Statement, RQs, Methodology Overview | Pre-thesis report |
| CO5 | Design multiple solutions | Ch3: 7 baselines + N1-N4 components + selector | P2: Ch4 |
| CO6 | Analyze and assess alternatives | Ch4: ablation table, significance tests, oracle analysis | Final report |
| CO7 | Complete final design | Ch4: cross-model conservative as official deployable result | Final report |
| CO8 | Use contemporary tools | Whisper, BGE/E5, CLIP, spaCy, TransNetV2, Ollama | Presentation |
| CO9 | Research and literature survey | Ch2: literature review, gap analysis, 34 references | P1 + Final |
| CO14 | Effective communication | 78-page thesis, 26-slide defense, supervisor brief | Defense |

---

## 4. Self-Scoring Against Rubric (Honest Assessment)

> Cannot create a Google Spreadsheet from code — you need to open the rubric link and fill it in manually. Below is the self-assessment to copy in:

| CO | Max Marks | Self-Score | Justification |
|---|---|---|---|
| CO1 (P1) | 2.5 | **2.5** | Problem clearly formulated, scoped, and motivated |
| CO5 (P2) | 5 | **4.5** | 7 baselines + 4 integrated methods; k-fold LOO done |
| CO5 (Defense) | 10 | **8** | Strong design rationale; cross-domain generalization shown |
| CO6 (Defense) | 5 | **4** | Ablation is thorough; leave-domain-out test included |
| CO6 (Supervisor) | 5 | **4** | Statistical significance rigorously tested |
| CO7 | 5 | **4** | Final design delivered; deployment limitations honest |
| CO8 (Defense) | 5 | **4.5** | All major modern tools used correctly |
| CO8 (Supervisor) | 5 | **4** | Tool choices explained and justified |
| CO9 (P1) | 2.5 | **2.5** | Literature comprehensive |
| CO9 (Supervisor) | 2.5 | **2** | Some classic references could be expanded |
| CO14 (P2 Poster) | 5 | **4** | Defense slides v4 ready; 26 structured slides |
| CO14 (Defense) | 10 | **8** | Thesis is well-structured and clearly written |
| CO14 (Supervisor) | 5 | **4** | Writing improved; AI-sounding sections fixed |
| **Total (self)** | **67.5** | **~55.5** | Approx 82% |

---

## 5. Overleaf Editable Link

To share on Overleaf:
1. Go to https://overleaf.com → New Project → Upload Project
2. Zip the `thesis/` folder: `thesis/main.tex`, all `thesis/chapters/`, `thesis/frontmatter/`, `thesis/appendices/`, `thesis/bibliography/`, `thesis/tables/`, `thesis/figures/`
3. Upload the zip → Share → Turn on Link Sharing → set to "Can Edit"
4. Send the link

> I cannot create an Overleaf account or upload files on your behalf. The LaTeX source is fully self-contained in the `thesis/` directory.

---

## 6. Turnitin Submission

To submit to Turnitin:
1. Log in with your student account
2. Go to the class your supervisor created
3. Submit `thesis/main.pdf` (78 pages)
4. The paper will appear under whichever numbered submission slot you choose (1–10)

> I do not have access to your Turnitin credentials or class ID. You must do this step yourself.

---

## 7. All Relevant Files (Folder Structure)

The GitHub repository at https://github.com/IsmamK/Thesis_TopicSegmentation contains:

```
thesis/
  main.pdf               ← Final thesis (78 pages)
  main.tex               ← LaTeX source
  chapters/              ← All 6 chapters + conclusion + future work
  appendices/            ← 3 appendices (dataset, hyperparameters, extra results)
  figures/               ← All figures including new external eval charts
  tables/                ← All auto-generated LaTeX tables
  bibliography/          ← references.bib (34 entries)
  LECSEG_Defense_Slides_v4.pptx  ← 26-slide defense deck
  supervisor_brief.pdf   ← 1-page supervisor reference sheet

docs/
  supervisor_brief.tex   ← LaTeX source for supervisor brief
  supervisor_brief.pdf
  PROGRESS_LOG.md        ← Full session-by-session lab notebook
  supervisor_review/     ← THIS folder

results/
  external_eval.json     ← External validation raw results

scripts/
  external_eval.py       ← Reproducible external validation script
  pipeline.py            ← Full end-to-end pipeline
  run_eval.py            ← Ablation battery

src/lecseg/             ← All model/evaluation source code
data/                   ← Transcripts, sentences, embeddings, ground truth
```

---

## 8. Response to Supervisor's Specific Questions

**Q1: Spreadsheet with self-scoring against rubric**  
See Section 4 above. Fill into the rubric spreadsheet manually.

**Q2: Compliance with paper-writing checklist**  
See Section 2 above. All major checklist items addressed. Remaining gap: PNG charts (checklist prefers vector/PDF) — the external eval charts are PNG; the existing thesis figures are PDF/vector. This will be fixed in the next iteration.

**Q3: Turnitin submission**  
Cannot submit without your credentials. PDF is ready at `thesis/main.pdf`.

**Q4: Overleaf editable link**  
See Section 5 above — instructions to upload yourself.

**Q5: Folder with all files**  
The GitHub repository IS the complete folder. All files are committed and pushed.
